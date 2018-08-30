#!/usr/bin/env python
"""
run.py: Execute iometer test as per config.py
"""

# from python lib
import os
import sys
import time
import subprocess

# from qcs automations libs
import config
from nodes.node import Linux
from libs.log.logger import Log
from libs.ovirt_engine import OvirtEngine

# create log object
log = Log()


def check_firewalld(node):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = node.conn.execute_command("firewall-cmd --state")
        if stderr and 'not' in stderr[0]:
            log.info("Firewall is not running")
        else:
            command = 'systemctl stop firewalld'
            _, stdout, stderr = node.conn.execute_command(command)
            log.warn("Firewall is stopped, please start the firewall +\
                      once execution completes")
    except Exception as e:
        log.error("Something went wrong", str(e))

def get_current_host_ip():
    """
    Gets IP of current machine
    """
    ip = subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)
    ip = ip.decode(encoding='UTF-8',errors='strict')
    return ip.rstrip('\n')

def start_iometer(master, slave_nodes, current_host_ip, configfile):
    """
    Start Dynamo on slave nodes and iometer on client node
    :param master - ssh connection iometer server(windows)
    :param slave_nodes - ssh connection to slave nodes(linux)
    :param current_host_ip - ip of the current machine
    :param configfile - configuration file to be used
    :return - None
    """
    for slave_vm in slave_nodes:
         # copy dynamo on slave machine
         slave_vm.conn.copy_command(config.LOCAL_PATH, config.REMOTE_PATH)
         slave_vm.conn.execute_command('chmod +x %s' %config.REMOTE_PATH)

         # start dynamo on slave machine
         _, stdout, stderr = \
             slave_vm.conn.execute_command(
             "nohup /root/dynamo -i '{0}' -m '{1}' > /dev/null 2>&1 &\n"\
             .format(master.ip, slave_vm.ip))
         log.info("Started Dynamo on client {}".format(slave_vm.ip))

    # remove if existing config and result file on master node
    _, stdout, stderr = \
        master.conn.execute_command("cmd \/c del /f {0}result.csv"\
                                    .format(config.IOMETER_SDK))
    _, stdout, stderr = \
        master.conn.execute_command("cmd \/c del /f {0}{1}"\
                                    .format(config.IOMETER_SDK,
                                    config.IOMETER_CONFIG_FILE))

    # copy iometer configuration file on iometer server
    status, stdout, stderr = \
        master.conn.execute_command(
        "cmd \/c echo y | pscp.exe -pw {2} {1}@{0}:{3} {4}"\
        .format(current_host_ip, config.CURRENT_UNAME, config.CURRENT_PASSWD,
                configfile, config.IOMETER_SDK))
    if status:
        log.info(stdout)
        log.error(stderr)
        sys.exit(1)

    # start iometer on Iometer server
    status, stdout, stderr = \
        master.conn.execute_command(
        "cmd \/c {0}IOmeter.exe /c {0}test_iometer.icf /r {0}result.csv /t 15"\
        .format(config.IOMETER_SDK))
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("IOMeter completed successfully.")

    # copy result file into output dir
    output_directory = os.path.abspath(config.IOMETER_OUTPUT_DIR)
    _, stdout, stderr = \
        master.conn.execute_command(
        "cmd \/c echo y | pscp.exe -pw {2} {4}result.csv {1}@{0}:{3}"\
        .format(current_host_ip, config.CURRENT_UNAME, config.CURRENT_PASSWD,
                output_directory, config.IOMETER_SDK))

def create_configuration_file(slave_nodes, configfile):
    """
    Add the number of slave client and disk to configuration file.
    :param slave_nodes: Command to be executed
        :return: None

    """
    target_info = list()
    target_info = ["'Target",
                   "\tdummay_disk",
                   "'Target type",
                   "\tDISK",
                   "'End target"]

    for slave_vm in slave_nodes:
         # get disk name from slave
         slave_vm.refresh_disk_list()
         disks = [disk.split('/')[-1] for disk in slave_vm.disks]

         flag = False
         # write disk name and ip address to config file
         with open("iometer.icf") as fd:
             with open(configfile, "w") as fd1:
                 for line in fd:
                     if line.startswith("\'Manager network address"):
                         fd1.write(line)
                         flag = True
                         data = str(slave_vm) + "\n"
                     elif line.startswith("\'Target assignments"):
                         fd1.write(line)
                         for disk in disks:
                             # update the disk name in target_info
                             target_info[1] = "\t" + disk 
                             # write target_info in file
                             for line_info in target_info:
                                 fd1.write(line_info + "\n")
                     elif flag:
                         fd1.write(data)
                         flag = False
                     else:
                         fd1.write(line)

def main():
    """
    Standalone iometer execution steps:
    precondition: update config.py as per need
    1. create vms
    2. add disks
    3. choose file/block IO
    4. start iometer load in foreground
    """
    log_dir = config.LOG_DIR 
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, "iometer_stdout.log")
    log.initialise(logfile, config.LOG_LEVEL)
    log.info("Logs will be collected in '{}' directory".format(log_dir))
    log.info("logfile: {}".format(logfile))

    ovirt = OvirtEngine(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                        config.OVIRT_ENGINE_PASS)

    log.info("Remove existing vms if any")
    for i in range(config.SLAVE_VM_COUNT):
        # search if vm is already present
        vm = ovirt.search_vm(config.VM_NAME + str(i))
        if vm:
            # stop the vm
            ovirt.stop_vm(config.VM_NAME + str(i))
            # remove vm
            ovirt.remove_vm(config.VM_NAME + str(i))

    log.info("Step 1. Creating {} VM(s)".format(config.SLAVE_VM_COUNT))
    vms = list()
    for i in range(config.SLAVE_VM_COUNT):
        vm_name = config.VM_NAME + str(i)
        vm = ovirt.create_vm_from_template(vm_name,
                                           config.CLUSTER_NAME,
                                           config.TEMPLATE_NAME,
                                           config.TEMPLATE_DS)
        vms.append(vm)

    log.info("Sleeping for 1 minute for vm IP to be available.")
    time.sleep(60)

    # get vm ips
    vm_ips = list()
    for vm in vms:
         ip = ovirt.get_vm_ip(vm.name)
         vm_ips.append(ip)
    log.info("VM IPs are: {}".format(vm_ips))
    if not vm_ips:
        log.critical("No vm IP found")
        sys.exit(1)

    log.info("Creating host objects") 
    host_list = list()
    for vm in vm_ips:
        if config.HOST_TYPE.lower() == 'linux':
            host = Linux(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
            check_firewalld(host)
        elif config.HOST_TYPE.lower() == 'windows':
            # host = Windows(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
            pass
        else:
            log.error("Unknown host type - {}".format(config.HOST_TYPE))
        # update available disks
        host_list.append(host)
    # get master host
    master_host = Linux(config.IOMETER_SERVER, config.IOMETER_UNAME,
                        config.IOMETER_PASSWD)

    # Add disks
    log.info("Step 2. Add disk to VM(s)")
    for vm in vms:
         for i in range(config.DISK_COUNT):
            ovirt.add_disk(vm.name,
                           "disk_" + str(i),
                           config.DISK_SIZE_GB,
                           config.TEMPLATE_DS)

    log.info("Step 3. Create config file based on load type")
    output_configfile = os.path.join(log_dir, config.IOMETER_CONFIG_FILE)
    output_configfile = os.path.abspath(output_configfile)
    log.info("Output configuration file {}".format(output_configfile))
    create_configuration_file(host_list, output_configfile)
    current_host_ip = get_current_host_ip()
    log.info(current_host_ip)

    log.info("Step 4. Do prerequisite and start iometer.")
    start_iometer(master_host, host_list, current_host_ip, output_configfile)
    ovirt.close_connection()


if __name__ == '__main__':
    main()

