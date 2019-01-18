#!/usr/bin/env python
"""
run.py: Execute fio test as per config.py
"""

# from python lib
import sys
import time
import os
import shutil
import subprocess
import threading
import configparser

# from qcs-automation libs
from libs.ovirt_engine import OvirtEngine
from libs.log.logger import Log
from tools.qcsbench.fio import config
from nodes.node import Linux, Windows

# create a log object
if os.environ.get('USE_ROBOT_LOGGER', None) == "True":
    from libs.log.logger import Log

    log = Log()
else:
    log = Log()

FIO_REMOTE_PATH = "/root/fio/"
WIN_FIO_EXE_LOC = "C:\\FIO\\"


def check_firewall(host):
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
        log.info("Something went wrong")


def get_master_ip():
    """
    Gets IP of current machine
    """
    ip = subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)
    ip = ip.decode(encoding='UTF-8', errors='strict')
    return ip.rstrip('\n')


def create_window_file_io_file(host):
    for value in range(1, (config.DISK_COUNT + 1)):
        filename = "window_file_io_" + str(value) + ".txt"
        curr_dir = os.getcwd()
        file_dir = os.path.join(curr_dir, filename)
        content = open(file_dir, 'w')
        content.write('select disk ' + str(value) + '\nattribute disk clear readonly noerr\n\
                       online disk noerr\nlist partition\nconvert gpt noerr\n\
                       create partition primary\nlist partition\nselect partition 2\n\
                       detail partition\nformat quick FS=ntfs label="mount_point" \n\
                       assign mount=C:\mountpoint\ndetail partition')
        content.close()
        host.conn.scp_put(localpath=file_dir, remotepath="FIO")


def block_io_linux(host, ip):
    # start dynamo on host machine
    host.conn.edit_load_file_for_block_io(host.disk_list,
                                          path_load_file="{}{}".format
                                          (FIO_REMOTE_PATH,
                                          config.FIO_CONF_FILE))
    log.info("Step 4. Start fio load on raw device.")
    status, stdout, stderr = host.conn.execute_command("fio {}{} --output={}{}"
                                                       .format(FIO_REMOTE_PATH,
                                                       config.FIO_CONF_FILE,
                                                       FIO_REMOTE_PATH,
                                                       config.FIO_RESULT_FILE))
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("FIO completed successfully.")
    log_dir = config.LOG_DIR
    log_dir = os.path.join(log_dir, ip)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    res_file = os.path.join(log_dir, "{}".format(config.FIO_RESULT_FILE))
    log.info("Fio logs will be collected in '{}' directory".format(log_dir))
    log.info("res_file: {}".format(res_file))
    host.conn.scp_get(remotepath="{}{}".format(FIO_REMOTE_PATH,
                      config.FIO_RESULT_FILE),
                      localpath="{}".format(res_file))
    conf_file = os.path.join(log_dir, "{}".format(
        config.FIO_CONF_FILE))
    log.info("conf_file: {}".format(conf_file))
    host.conn.scp_get(remotepath="{}{}".format(FIO_REMOTE_PATH,
                      config.FIO_CONF_FILE),
                      localpath="{}".format(conf_file))
    log.info(stdout)


def file_io_linux(host, ip):
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
    host.conn.edit_load_file_for_file_io(host.mount_locations,
                                         path_load_file="{}{}".format(
                                         FIO_REMOTE_PATH,
                                         config.FIO_CONF_FILE))
    # start dynamo on host machine
    log.info("Step 4. Start fio load on file system device.")
    status, stdout, stderr = host.conn.execute_command("fio {}{} --output={}{}"
                                                       .format(FIO_REMOTE_PATH,
                                                       config.FIO_CONF_FILE,
                                                       FIO_REMOTE_PATH,
                                                       config.FIO_RESULT_FILE))
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("FIO completed successfully.")
    log_dir = config.LOG_DIR
    log_dir = os.path.join(log_dir, ip)
    os.makedirs(log_dir)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    res_file = os.path.join(log_dir, "{}".format(
        config.FIO_RESULT_FILE))
    log.info("Fio logs will be collected in '{}' directory".format(
        log_dir))
    log.info("res_file: {}".format(res_file))
    host.conn.scp_get(remotepath="{}{}".format(FIO_REMOTE_PATH,
                      config.FIO_RESULT_FILE),
                      localpath="{}".format(res_file))
    conf_file = os.path.join(log_dir, "{}".format(config.FIO_CONF_FILE))
    log.info("conf_file: {}".format(conf_file))
    host.conn.scp_get(remotepath="{}{}".format(FIO_REMOTE_PATH,
                      config.FIO_CONF_FILE),
                      localpath="{}".format(conf_file))
    log.info(stdout)


def start_fio_for_linux(host, ip):
    """
    Start fio on host
    :param host_list: ssh connection to hosts(linux)
    """
    # install fio on host
    check_firewall(host)
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
    log.info("Step 3. Choose file/block IO")
    if 'block_io' in config.LOAD_TYPE:
        block_io_linux(host, ip)
    elif 'file_io' in config.LOAD_TYPE:
        file_io_linux(host, ip)


def block_io_window(host, ip, CURRENT_HOST_IP, thread_id):
    # start dynamo on host machine
    # host.conn.edit_load_file_for_block_io(host.disk_list,
    #                                      path_load_file="FIO\\{}".format
    #                                      (config.FIO_CONF_FILE))
    log.info(host.disk_list)
    file_name = str(thread_id) + "_{}".format(config.FIO_CONF_FILE)
    shutil.copyfile("sample_test_fio_wind.fio", file_name)
    for disk in host.disk_list:
        log.info(disk)
        log.info("disk= {} ".format(disk))
        conf = configparser.RawConfigParser()
        sec = 'job_' + disk
        conf.add_section(sec)
        conf.set(sec, 'filename', disk)

        with open(file_name, 'a+') as configfile:
            conf.write(configfile, space_around_delimiters=False)

    host.conn.scp_put(localpath=file_name, remotepath="FIO")
    os.remove(file_name)
    log.info("Step 4. Start fio load on raw device.")
    status, stdout, stderr = host.conn.execute_command("cmd /c fio {}{} "
                                                       "--output={}{}"
                                                       .format(WIN_FIO_EXE_LOC,
                                                       os.path.basename
                                                       (file_name),
                                                       WIN_FIO_EXE_LOC,
                                                       os.path.basename(
                                                       config.FIO_RESULT_FILE)))
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("FIO completed successfully.")
    log_dir = config.LOG_DIR
    log_dir = os.path.join(log_dir, str(ip))
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log.info("Fio logs will be collected in '{}' directory".format(
        log_dir))
    output_directory = os.path.abspath(log_dir)
    _, stdout, stderr = host.conn.execute_command(
               "cmd /c echo y | pscp -pw {2} {4}{5} {1}@{0}:{3}" \
               .format(CURRENT_HOST_IP, config.USERNAME, config.PASSWORD,
               output_directory, WIN_FIO_EXE_LOC, config.FIO_RESULT_FILE))
    _, stdout, stderr = host.conn.execute_command(
               "cmd /c echo y | pscp -pw {2} {4}{5} {1}@{0}:{3}" \
               .format(CURRENT_HOST_IP, config.USERNAME, config.PASSWORD,
               output_directory, WIN_FIO_EXE_LOC, file_name))
    log.info(stdout)


def file_io_window(host, ip, CURRENT_HOST_IP, thread_id):
    create_window_file_io_file(host)
    host.create_file_system_on_disks(config.TOOL_NAME)
    log.info("Filesystem locations available are - {}" \
             .format(host.filesystem_locations))
    log.info("Disks are: {}".format(host.disk_list))
    # host.conn.edit_load_file_for_file_io(host.filesystem_locations,
    #                                     path_load_file="C:\\FIO\\{}".format(
    #                                     config.FIO_CONF_FILE))
    # start dynamo on host machine
    file_name = str(thread_id) + "_{}".format(config.FIO_CONF_FILE)
    shutil.copyfile("sample_file_io_wind.fio", file_name)
    for disk in host.filesystem_locations:
        log.info("disk= {} ".format(disk))
        conf = configparser.RawConfigParser()
        sec = 'job_file'
        conf.add_section(sec)
        conf.set(sec, 'directory', disk)

        with open("{}".format(file_name), 'a+') as configfile:
            conf.write(configfile, space_around_delimiters=False)

    host.conn.scp_put(localpath="{}".format(file_name), remotepath="FIO")
    os.remove(file_name)
    log.info("Step 4. Start fio load on file system device.")
    host.conn.execute_command("cmd /c cd {}".format(WIN_FIO_EXE_LOC))
    status, stdout, stderr = host.conn.execute_command("cmd /c fio {}{} "
                                                       "--output={}{}"
                                                       .format(WIN_FIO_EXE_LOC,
                                                       os.path.basename
                                                       (file_name),
                                                       WIN_FIO_EXE_LOC,
                                                       os.path.basename(
                                                       config.FIO_RESULT_FILE)))
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("FIO completed successfully.")
    log_dir = config.LOG_DIR
    log_dir = os.path.join(log_dir, ip)
    os.makedirs(log_dir)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    log.info("Fio logs will be collected in '{}' directory".format(
        log_dir))
    output_directory = os.path.abspath(log_dir)
    _, stdout, stderr = host.conn.execute_command(
        "cmd /c echo y | pscp -pw {2} {4}{5} {1}@{0}:{3}" \
            .format(CURRENT_HOST_IP, config.USERNAME, config.PASSWORD,
                    output_directory, WIN_FIO_EXE_LOC, config.FIO_RESULT_FILE))
    _, stdout, stderr = host.conn.execute_command(
        "cmd /c echo y | pscp -pw {2} {4}{5} {1}@{0}:{3}" \
            .format(CURRENT_HOST_IP, config.USERNAME, config.PASSWORD,
                    output_directory, WIN_FIO_EXE_LOC, file_name))
    log.info(stdout)


def start_fio_for_windows(host, ip, CURRENT_HOST_IP, thread_id):
    """
        Start fio on host
        :param host_list: ssh connection to hosts(linux)
    """
    # check if fio directory, result.txt and config file already exists.
    # then remove it.
    file_name = str(thread_id) + "{}".format(config.FIO_CONF_FILE)
    host.conn.execute_command("cmd /c if not exist {} mkdir {}".format(
                              WIN_FIO_EXE_LOC, WIN_FIO_EXE_LOC))
    host.conn.execute_command("cmd /c if exist {}{} del {}{}".format(
                              WIN_FIO_EXE_LOC, file_name,
                              WIN_FIO_EXE_LOC, file_name))
    host.conn.execute_command("cmd /c if exist {}{} del {}{}"
                              .format(WIN_FIO_EXE_LOC, config.FIO_RESULT_FILE,
                              WIN_FIO_EXE_LOC, config.FIO_RESULT_FILE))
    # copy fio config file on host machine
    host.refresh_disk_list()
    log.info("Step 3. Choose file/block IO")
    if 'block_io' in config.LOAD_TYPE:
        block_io_window(host, ip, CURRENT_HOST_IP, thread_id)
    elif 'file_io' in config.LOAD_TYPE:
        file_io_window(host, ip, CURRENT_HOST_IP, thread_id)


def create_vms(thread_id, ovirt):

    """
    Standalone fio execution steps:
    precondition: update config.py as per need
    1. create vms
    2. add disks
    3. choose file/block IO
    4. Start fio load in foreground
    """

    log.info("Step 1. Creating {} VM(s)".format(config.SLAVE_VM_COUNT))

    vm_name = config.VM_NAME + str(thread_id)
    vm = ovirt.create_vm_from_template(vm_name,
                                       config.CLUSTER_NAME,
                                       config.TEMPLATE_NAME,
                                       config.TEMPLATE_DS)

    # get vms ips
    attempt_for_ip = 1
    while (attempt_for_ip < 11):
        ip = ovirt.get_vm_ip(vm.name)
        if ip:
            log.info("IP found for host {}".format(vm.name))
            break
        attempt_for_ip += 1
        if (attempt_for_ip == 11):
            log.critical("No IP found for host {}".format(vm.name))
            sys.exit(1)
        time.sleep(30)
    log.info("VM IPs are: {}".format(ip))

    log.info("Creating host objects")

    if config.HOST_TYPE.lower() == 'linux':
        host = Linux(str(ip), config.SLAVE_UNAME, config.SLAVE_PASSWORD)
    elif config.HOST_TYPE.lower() == 'windows':
        host = Windows(str(ip), config.SLAVE_UNAME, config.SLAVE_PASSWORD)
        pass
    else:
        log.error("Unknown host type - {}".format(config.HOST_TYPE))
    # update available disks

    # Add disks
    log.info("Step 2. Add disk to VM(s)")
    for i in range(len(config.INTERFACES)):
        ovirt.add_disk(vm.name,
            "disk_" + str(i),config.INTERFACES[i],
            config.DISK_SIZE_GB,
            config.TEMPLATE_DS,
            config.STORAGE_TYPE)
        while ((ovirt.get_vm_ip(vm.name) == None) or (ovirt.get_vm_ip(vm.name)
                == "")):
                continue

    CURRENT_HOST_IP = get_master_ip()
    log.info(CURRENT_HOST_IP)
    if config.HOST_TYPE.lower() == 'linux':
        start_fio_for_linux(host, ip)
    elif config.HOST_TYPE.lower() == 'windows':
        start_fio_for_windows(host, ip, CURRENT_HOST_IP, thread_id)

    # stop the vm
    # ovirt.stop_vm(vm.name)
   

def main():
    if os.path.isdir(config.LOG_DIR):
        shutil.rmtree(config.LOG_DIR)
    log_dir = config.LOG_DIR
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, "fio_stdout.log")
    log.initialise(logfile, config.LOG_LEVEL)
    log.info("Logs will be collected in '{}' directory".format(log_dir))
    log.info("logfile: {}".format(logfile))

    ovirt = OvirtEngine(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                        config.OVIRT_ENGINE_PASS)
    i = 0
    vm = True
    while(vm):
        vm = ovirt.search_vm(config.VM_NAME + str(i))
        if vm:
            # stop the vm
            ovirt.stop_vm(config.VM_NAME + str(i))
            # remove vm
            ovirt.remove_vm(config.VM_NAME + str(i))
            i+=1
        else:
            break
    
    jobs = []
    for thread_id in range(config.SLAVE_VM_COUNT):
        thread = threading.Thread(target=create_vms, args=(thread_id, ovirt,))
        jobs.append(thread)

    log.info(jobs)

    for j in jobs:
        j.start()
        log.info("Thread {}".format(j))

    for j in jobs:
        j.join()

    log.info("List processing complete.")
    
    ovirt.close_connection() 


if __name__ == '__main__':
    main()

