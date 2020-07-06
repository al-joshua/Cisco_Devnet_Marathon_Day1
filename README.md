# Cisco Devnet Marathon Day1

## Task

The task is to wright a script which performs the following set of actions:

1. Pull running-config from all the devices and save it to a separate folder.
2. Explore CDP on a device. Return if its ON or Off and the number of neighbors.
3. Check the software image version. Return the image name and also explore whether it is PE (Payload Encryption) or NPE
 (Non Payload Encryption).
4. Configure NTP on a switch. Check if time is synchronised on a switch. If not configured, configure the NTP server and
 timezone. Return the ntp server sync status and current time.

Print the cummulative output of the performed actions in the following string format:

`Hostname | Device model | Software image | {PE|NPE} | CDP is {ON|OFF}, Number of adjacencies | Clock status`


## Script Description

For the sake of simplicity and given the small size of the testbed, the list of IP addresses for the script to poll
fed to the input as an argument in the form of a single string. Addresses must be listed through coma without spaces.

For example:

`python en_devnet_day1.py 10.177.1.2,10.177.1.3,10.177.1.4`

The script performs a basic check for the presence of an input string. To establish a connection, a username and password will be requested.
The script also handles errors that may occur during the connection setup.

In a test environment several IOS-based switches (c2960, c3560, c3750) were used, as well as a pair of 
routers (2800, 2900 series).
Netmiko is used as a client, telnet is used as a protocol.

Each subtask is implemented as a separate function. The script saves the current device configurations to the selected
_output directory, which is created automatically.
The script outputs to the terminal all the collected information in the structure described in the task.
