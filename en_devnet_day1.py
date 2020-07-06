#!/usr/bin/env python3

from netmiko import ConnectHandler
from netmiko import ssh_exception
from datetime import date
import getpass
import os
import sys
import time
import re

# folder to store configs
output_directory = "_output"

# ntp server ip address to configure
ntp_server = '10.177.0.1'

# clock commands to configure
clock_commands = ['clock timezone GMT 0', f'ntp server {ntp_server}']


def connect_to_device(ip, usr, passwd, enable_pass, proto='cisco_ios_telnet'):
    ''' function sets the connection to the devices via netmiko client '''

    device_params = {
        'device_type': proto,
        'ip': ip,
        'username': usr,
        'password': passwd,
        'secret': enable_pass,
        'verbose': True,
        'session_timeout': 10
    }

    try:
        conn = ConnectHandler(**device_params)
    except (TimeoutError, ConnectionRefusedError, ConnectionResetError, ValueError,
            ssh_exception.NetmikoAuthenticationException) as err:
        print(err)
        conn = None

    return conn


def sh_run(session):
    ''' function polls current configurations '''

    hostname = session.send_command('sh run | in hostname').split()[1]
    run_config = session.send_command('sh run')

    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    with open(os.path.join(output_directory, str(date.today()) + '_' + hostname), 'w') as f:
        f.write(run_config)

    return hostname


def cdp(session):
    ''' function analyses CDP status and adjacency's '''

    cdp_entries_count = 0
    cdp_status = True

    cdp_response = session.send_command('sh cdp entry * | in Device.ID')

    if 'CDP is not enabled' in cdp_response:
        cdp_status = False
    else:
        if 'Device ID' in cdp_response:
            cdp_entries_count = len(cdp_response.split('\n'))

    return 'ON' if cdp_status else 'OFF', cdp_entries_count


def image(session):
    ''' The Function analyses software image and type '''

    image_type = 'PE'
    device_type = session.send_command('sh version | in bytes of memory').split()[1]

    try:
        device_image = re.search('[\w.-]+bin', session.send_command('sh version | in System image').split()[-1]).group()
    except Exception() as err:
        print(f'failed to parse the software image name. Error {err}')

    if 'npe' in device_image:
        image_type = 'NPE'

    return image_type, device_type, device_image


def ntp(session):
    ''' function pre-checks the availability of the NTP host through PING. If successful, sets up
      ntp server and timezone. Returns the status of clock synchronization with the NTP server '''

    ntp_ping_response = session.send_command(f'ping {ntp_server}')
    ntp_sync_status = True

    if 'Success rate is 0 percent' in ntp_ping_response:
        ntp_sync_status = False
    else:
        session.send_config_set(clock_commands)
        time.sleep(5)
        ntp_status_result = session.send_command('sh ntp status | in Clock is')
        if 'synchronized' not in ntp_status_result:
            ntp_sync_status = False

    return 'SYNCED' if ntp_sync_status else 'NOT SYNCED'


def _main():
    ''' main function, collects everything together '''

    # for simplicity, device addresses are supplied to the script input as a comma-separated list (without spaces)
    try:
        device_list = sys.argv[1].split(',')
    except IndexError:
        print('Provide a list of ip addresses separated by comma w/o spaces\n'
              'E.g: 192.168.1.1,192.168.2.1,192.168.12.1')
        sys.exit(1)

    user = input('Username: ')
    password = getpass.getpass(prompt='Enter password: ')
    enable_secret = getpass.getpass(prompt='Enter enable password: ')

    for ip in device_list:
        # initiate the connection to a device
        sess = connect_to_device(ip, user, password, enable_secret)
        if sess:

            # get the hostname and pull the config
            hostname = sh_run(sess)

            # get the required cdp info
            cdp_status, cdp_entries_count = cdp(sess)

            # get the required software image info
            image_type, device_type, device_image = image(sess)

            # set up the NTP and analyze its status
            ntp_sync_status = ntp(sess)

            # print the cumulative output
            print(f'{hostname} | {device_type} | {device_image} | {image_type} | '
                  f'CDP is {cdp_status}, {cdp_entries_count} peers | Clock in {ntp_sync_status}')

        else:
            print(f'Failed to connect to {ip}')


if __name__ == '__main__':
    _main()