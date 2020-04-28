#!/usr/bin/env python3

from netmiko import ConnectHandler
from netmiko import ssh_exception
from datetime import date
import getpass
import os
import sys
import time
import re

# директория для сбора конфигураций
output_directory = "_output"

# ip адрес ntp сервера (заменить на свой)
ntp_server = '10.177.0.1'

# команды для настройки времени и NTP
clock_commands = ['clock timezone GMT 0', f'ntp server {ntp_server}']


def connect_to_device(ip, usr, passwd, enable_pass, proto='cisco_ios_telnet'):
    ''' Функция устанавливает телнет соединение с устройством и возвращает объект сессии '''

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
    ''' Функция сохраняет текущую конфигурацию устройства в файл а также возвращает имя хоста '''

    hostname = session.send_command('sh run | in hostname').split()[1]
    run_config = session.send_command('sh run')

    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    with open(os.path.join(output_directory, str(date.today()) + '_' + hostname), 'w') as f:
        f.write(run_config)

    return hostname


def cdp(session):
    ''' Функция собирает и анализиурет вывод информации о CDP. Возвращает статус и число соседств'''

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
    ''' Функция собирает и анализарует вывод sh version. Возвращает тип ПО (PE|NPE), модель устройства
    и имя образа ПО '''

    image_type = 'PE'
    device_type = session.send_command('sh version | in bytes of memory').split()[1]
    device_image = re.search('[\w.-]+bin', session.send_command('sh version | in System image').split()[-1]).group()

    if 'npe' in device_image:
        image_type = 'NPE'

    return image_type, device_type, device_image


def ntp(session):
    ''' Функция выполняет предварительную проверку досутпность хоста NTP посредсовм PING. В случае успеха настраивает
     ntp server и timezone. Возвращает статус синхронизации часов с сервером NTP '''

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
    ''' Главная функция, собирает все вместе '''

    # для простоты адреса устройств подаются на вход скрипта в виде списка через запятую (без пробелов)
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
        # для каждого устройства из списка устанавливаем соединение
        sess = connect_to_device(ip, user, password, enable_secret)
        if sess:

            # получаем имя устройства и копируем конфиг
            hostname = sh_run(sess)

            # получвем необходимую информацию о CDP
            cdp_status, cdp_entries_count = cdp(sess)

            # получаем необходимую информацию об образе ПО
            image_type, device_type, device_image = image(sess)

            # настраиваем NTP и получаем статус
            ntp_sync_status = ntp(sess)

            # выводим на экран полученную информацию
            print(f'{hostname} | {device_type} | {device_image} | {image_type} | '
                  f'CDP is {cdp_status}, {cdp_entries_count} peers | Clock in {ntp_sync_status}')

        else:
            print(f'Failed to connect to {ip}')


if __name__ == '__main__':
    _main()