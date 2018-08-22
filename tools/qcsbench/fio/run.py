#!/usr/bin/env python
"""
run.py: Execute fio test as per config.py
"""

# from python lib
import sys
import time
import os
import subprocess

# from qcs-automation libs
from libs.ovirt_engine import OvirtEngine
from libs.log.logger import Log
from tools.qcsbench.fio import config
from nodes.node import Linux

# create a log object
if os.environ.get('USE_ROBOT_LOGGER', None) == "True":
    from libs.log.logger import Log
    log = Log()
else:
    log = Log()

FIO_REMOTE_PATH = "/root/fio/"
WIN_FIO_EXE_LOC = "c:\\fio"
WIN_FIO_LOGS = "c:\\fio\\output"


def check_firewalld(host):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = host.conn.execute_command("firewall-cmd --state")
        if stderr and 'not' in stderr[0]:
            log.info("Firewall is not running")
        else:
            command = 'systemctl stop firewalld'
            _, stdout, stderr = host.conn.execute_command(command)
            log.warn("Firewall is stopped, please start the firewall +\
                      once execution completes")
    except Exception as e:
        print("Something goes wrong")

def get_master_ip():
    """
    Gets IP of current machine
    """
    ip = subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)
    ip = ip.decode(encoding='UTF-8', errors='strict')
    return ip.rstrip('\n')

def start_fio(host_list):
    """
    Start fio on host
    :param host_list: ssh connection to hosts(linux)
    """
    for host in host_list:
        # install fio on host
        check_firewalld(host)
        host.deploy('fio')
        # check if fio directory, result.txt and config file already exists.
        # then remove it.
        host.conn.execute_command("[ -d {} ] || mkdir {}".format(
                                  FIO_REMOTE_PATH, FIO_REMOTE_PATH))
        host.conn.execute_command("[ -f {}{} ] && rm -rf {}{}".format(
                                  FIO_REMOTE_PATH, config.FIO_CONF_FILE,
                                  FIO_REMOTE_PATH, config.FIO_CONF_FILE))
        host.conn.execute_command("[ -f {}{} ] && rm -rf {}{}".format(
                                  FIO_REMOTE_PATH, config.FIO_RESULT_FILE,
                                  FIO_REMOTE_PATH, config.FIO_RESULT_FILE))
        # copy fio config file on host machine
        host.conn.scp_put(localpath="{}".format(config.FIO_CONF_FILE),
                          remotepath="{}{}".format(FIO_REMOTE_PATH,
                          config.FIO_CONF_FILE))
        host.refresh_disk_list()

        host.conn.edit_load_file(host.disk_list, path_load_file="{}{}".format(
                                 FIO_REMOTE_PATH, config.FIO_CONF_FILE))
        log.info("Step 3. Choose file/block IO")
        if 'block_io' in config.LOAD_TYPE:
            # start dynamo on host machine
            log.info("Step 4. Start fio load on raw device.")
            status, stdout, stderr = host.conn.execute_command("fio {}{} --output="
                                "{}{}".format(FIO_REMOTE_PATH,
                                config.FIO_CONF_FILE, FIO_REMOTE_PATH,
                                config.FIO_RESULT_FILE))
            if status:
                log.info(stdout)
                log.error(stderr)
            else:
                log.info("VDBench completed successfully.")
            log_dir = config.LOG_DIR
            log_dir = os.path.join(log_dir)
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)
            res_file = os.path.join(log_dir, "{}".format(
                                    config.FIO_RESULT_FILE))
            log.info("Fio logs will be collected in '{}' directory".format(
                     log_dir))
            log.info("res_file: {}".format(res_file))
            host.conn.scp_get(remotepath="{}{}".format(FIO_REMOTE_PATH,
                              config.FIO_RESULT_FILE), localpath=res_file)
            log.info(stdout)
        elif 'file_io' in config.LOAD_TYPE:
            host.create_file_system_on_disks()
            log.info("Filesystem locations available are - {}" \
                     .format(host.filesystem_locations))
            for i, location in enumerate(host.filesystem_locations):
                mount_point = "/mnt/loc{}".format(i)
                host.makedir(mount_point)
                # mount formatted device on host system
                cmd = "mount {} {}".format(location, mount_point)
                status, stdout, _ = host.conn.execute_command(cmd)
                if status:
                    log.info(stdout)
                    log.error("Unable to mount {} on {}" \
                              .format(location, mount_point))
                # append to mountpoints
                host.mount_locations.append(mount_point)
            log.info("Filesystem mount locations are {}" \
                     .format(host.mount_locations))
            log.info("Disks are: {}".format(host.disk_list))
            log.info("Step 4. Start fio load on file system device.")
            status, stdout, stderr = host.conn.execute_command("fio {}{} --output="
                                "{}{}".format(FIO_REMOTE_PATH,
                                config.FIO_CONF_FILE, FIO_REMOTE_PATH,
                                config.FIO_RESULT_FILE))
            if status:
                log.info(stdout)
                log.error(stderr)
            else:
                log.info("FIO completed successfully.")
            log_dir = config.LOG_DIR
            log_dir = os.path.join(log_dir)
            if not os.path.isdir(log_dir):
                os.makedirs(log_dir)
            res_file = os.path.join(log_dir, "{}".format(
                                    config.FIO_RESULT_FILE))
            log.info("Fio logs will be collected in '{}' directory".format(
                     log_dir))
            log.info("res_file: {}".format(res_file))
            host.conn.scp_get(remotepath="{}{}".format(FIO_REMOTE_PATH,
                              config.FIO_RESULT_FILE), localpath=res_file)
            log.info(stdout)

def main():
    """
    Standalone fio execution steps:
    precondition: update config.py as per need
    1. create vms
    2. add disks
    3. choose file/block IO
    4. Start fio load in foreground
    """
    log_dir = config.LOG_DIR
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, "fio_stdout.log")
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
        elif config.HOST_TYPE.lower() == 'windows':
            # host = Windows(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
            pass
        else:
            log.error("Unknown host type - {}".format(config.HOST_TYPE))
        # update available disks
        host_list.append(host)

    # Add disks
    log.info("Step 2. Add disk to VM(s)")
    for vm in vms:
        for i in range(config.DISK_COUNT):
            ovirt.add_disk(vm.name,
                           "disk_" + str(i),
                           config.DISK_SIZE_GB,
                           config.TEMPLATE_DS)

    this_server = get_master_ip()
    log.info(this_server)
    start_fio(host_list)


if __name__ == '__main__':
    main()

