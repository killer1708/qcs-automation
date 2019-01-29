#!/usr/bin/env python

# from python lib
import os
import sys
import time
import subprocess
import shutil
import threading
from shutil import copyfile

# from qcs automations libs
from tools.qcsbench.iometer import config
from nodes.node import Linux, Windows
from libs.log.logger import Log
from libs.ovirt_engine import OvirtEngine

# create log object
if os.environ.get('USE_ROBOT_LOGGER', None) == "True":
    from libs.log.logger import Log
    log = Log()
else:
    log = Log()
file_list=list()


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

def start_iometer(master, host, current_host_ip, configfile):
    """
    Start Dynamo on slave nodes and iometer on client node
    :param master - ssh coIOMETER_SERVERnnection iometer server(windows)
    :param slave_nodes - ssh connection to slave nodes(linux)
    :param current_host_ip - ip of the current machine
    :param configfile - configuration file to be used
    :return - None
    """
  
    # copy dynamo on slave machine
    host.conn.copy_command(config.LOCAL_PATH, config.REMOTE_PATH)
    host.conn.execute_command('chmod +x %s' %config.REMOTE_PATH)

    # start dynamo on slave machine
    _, stdout, stderr = \
         host.conn.execute_command(
         "nohup /root/dynamo -i '{0}' -m '{1}' > /dev/null 2>&1 &\n"\
        .format(master.ip, host.ip))
    log.info("Started Dynamo on client {}".format(host.ip))

    # remove if existing config and result file on master node
    _, stdout, stderr = \
        master.conn.execute_command("cmd \/c del /f {0}{1}"\
                                    .format(config.IOMETER_SDK,
                                            config.IOMETER_RESULT_FILE_NAME))
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
            "cmd \/c {0}IOmeter.exe /c {0}{1} /r {0}{2} /t 15" \
                .format(config.IOMETER_SDK, config.IOMETER_CONFIG_FILE,
                        config.IOMETER_RESULT_FILE_NAME))
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

def create_configuration_file(master, host, configfile):
    """
    Add the number of slave client and disk to configuration file.
    :param slave_nodes: Command to be executed
        :return: None

    """
    if os.path.isfile(configfile):
        os.remove(configfile)

    copyfile(config.BASE_IOMETER_FILE, configfile)
    fd1=open(configfile,'a')
    status, stdout, stderr = master.conn.execute_command("cmd \/c hostname" )
    data = "'Manager ID, manager name\n\t1," + str(stdout[0]) + \
           "\n'Manager network address\n\n'End manager\n"
    fd1.write(data)

    # get disk name from slave
    host.refresh_disk_list()
    disks = [disk.split('/')[-1] for disk in host.disks]
    print("disks", disks)
    # log.info("disks : ", disks)
    flag = False

    with open(config.BASE_IOMETER_FILE) as fd:
        i = 2
        status, stdout, stderr = host.conn.execute_command\
            ("hostname")
        data = "'Manager ID, manager name\n\t" + str(i) + "," + \
            str(stdout[0]) + "\n'Manager network address\n\t" + \
            str(host) + "\n"
        j = 1
        for j in range(1,int(config.WORKLOAD_INFO['no_of_worker'])+1):
            s = "'Worker\n\tworker" + str(j) + "\n'Worker type" + \
                "\n\tDISK" + "\n'Default target settings for " + \
                "worker\n'Number of outstanding IOs,test " + \
                "connection rate,transactions per connection,use " + \
                "fixed seed,fixed seed value\n\t1,DISABLED,1," + \
                "DISABLED,0\n'Disk maximum size,starting sector," + \
                "Data pattern\n\t" + \
                str(config.WORKLOAD_INFO["size_in_sector"]) + \
                ",0,0\n'End default target settings for worker\n" +\
                "'Assigned access specs\n\t"
            for value in range(len(config.WORKLOAD_INFO
                                   ["access_specification"])):
                 if value == len(config.WORKLOAD_INFO
                                 ["access_specification"]) - 1:
                     s += str(config.WORKLOAD_INFO
                              ["access_specification"][value])
                     s += "\n"
                 else:
                     s += str(config.WORKLOAD_INFO
                              ["access_specification"][value])
                     s += "\n\t"
            s += "'End assigned access specs\n'Target assignments\n"
            if(config.LOAD_TYPE=='file_io'):
                 file_list = host.mount_locations
                 if (len(file_list) == 0):
                     log.info("Sorry There is no available file list")
                     return
                 else:
                     for files in file_list:
                         s += "'Target\n\t" + str(files) + \
                              " [ext4]\n'Target type\n\tDISK\n" + \
                              "'End target\n"
                         s += "'End target assignments\n'End worker\n"
            elif(config.LOAD_TYPE=='block_io'):
                 for disk in disks:
                     s += "'Target\n\t" + disk + \
                          "\n'Target type\n\tDISK\n'End target\n"
                     s += "'End target assignments\n'End worker\n"
            else:
                print ("Load Type value is not correct")
                return
            data += s
            data += "'End manager\n'END manager list\nVersion 1.1.0"
            fd1.write(data)
    fd1.close()


def create_vms(thread_id, ovirt):
    """
    Standalone iometer execution steps:
    precondition: update config.py as per need
    1. create vms
    2. add disks
    3. choose file/block IO
    4. start iometer load in foreground
    """
    log.info("Step 1. Creating {} VM(s)".format(config.SLAVE_VM_COUNT))    

    vm_name = config.VM_NAME + str(thread_id)
    vm = ovirt.create_vm_from_template(vm_name,
                                       config.CLUSTER_NAME,
                                       config.TEMPLATE_NAME,
                                       config.TEMPLATE_DS)

    #log.info("Sleeping for 1 minute for vm IP to be available.")
    #time.sleep(60)

    # get vm ips
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
        pass
    elif config.HOST_TYPE.lower() == 'windows':
        host = Windows(str(ip), config.SLAVE_UNAME, config.SLAVE_PASSWORD)
        print("window login")
        pass
    else:
        log.error("Unknown host type - {}".format(config.HOST_TYPE))
        # update available disks
    # get master host
    master_host = Linux(config.IOMETER_SERVER, config.IOMETER_UNAME,
                        config.IOMETER_PASSWD)
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
    
    check_firewalld(host)
    host.refresh_disk_list()
    if config.LOAD_TYPE == 'block_io' :
        #change salve_vm name
        host.change_hostname()
    elif config.LOAD_TYPE == 'file_io' :
        #change salve_vm name
        host.change_hostname()
        # partition and format disk if its file_io
        host.create_file_system_on_disks()
        # list: get mount locations  ['/mnt/loc0', '/mnt/loc1']
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
        #file_list = host.mount_locations
        log.info("Disks are: {}".format(host.disk_list))

    log.info("Step 3. Create config file based on load type")
    log_dir = config.LOG_DIR
    output_configfile = os.path.join(log_dir, config.IOMETER_CONFIG_FILE)
    output_configfile = os.path.abspath(output_configfile)
    log.info("Output configuration file {}".format(output_configfile))
    create_configuration_file(master_host, host, output_configfile)
    current_host_ip = get_current_host_ip()
    log.info(current_host_ip)
    log.info("Step 4. Do prerequisite and start iometer.")
    start_iometer(master_host, host, current_host_ip, output_configfile)
    ovirt.close_connection()

def main():
    if os.path.isdir(config.LOG_DIR):
        shutil.rmtree(config.LOG_DIR)
    log_dir = config.LOG_DIR
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, "iometer_stdout.log")
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
        thread = threading.Thread(target=create_vms, args=(thread_id, ovirt, ))
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
