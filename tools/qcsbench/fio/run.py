import sys
import time
import subprocess
import config

from nodes.node import Linux
from libs.ovirt_engine import create_vm_from_template, get_vm_ip, \
                       vm_add_disk, remove_vm,search_vm, stop_vm
from libs.vdb_config import create_config

def check_firewalld(slave_node):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = slave_node.ssh_conn.execute_command('ls')
        print(stdout)
        _, stdout, stderr = slave_node.ssh_conn.execute_command("firewall-cmd --state")
        if stderr and b"not" in stderr[0]:
            print("Firewall not running ...")
        else:
            command = "systemctl stop firewalld"
            _, stdout, stderr = slave_node.ssh_conn.execute_command(command)
            print("Warning : Firewall is stopped, please start the firewall\
                   once execution is complete...")
    except Exception as e:
        print("Something goes wrong", str(e))

def get_master_ip():
    """
    Gets IP of current machine
    """
    ip = subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)
    ip = ip.decode(encoding='UTF-8',errors='strict')
    return ip.rstrip('\n')

def start_fio(slave_nodes, server):
    """
    Start fio on slave node
    :param slave_nodes: ssh connection to slave nodes(linux)
    :param server: ip of the current machine
        :return: None

    """
    for slave_vms in slave_nodes:
         # install fio on clinet
         slave_vms.deploy('fio')
         # check if fio directory and config already exists
         slave_vms.ssh_conn.copy_command("[ -d /root/fio ] || mkdir /root/fio")
         slave_vms.ssh_conn.copy_command("[-f /root/fio/test_fio.fio ] && rm -rf /root/fio/test_fio.fio")
         slave_vms.ssh_conn.copy_command("[-f /root/fio/result.txt ] && rm -rf /root/fio/result.txt")
         #copy fio config  on slave machine
         slave_vms.ssh_conn.copy_command("test_fio.fio", "/root/fio/test_fio.fio")

         #start dynamo on slave machine
         _, stdout, stderr = slave_vms.ssh_conn.execute_command("fio fiosample.fio --output=/root/fio/result.txt")
         print(stdout)

    return None

def configuration_file(slave_nodes):
    """
    Add the number of slave client and disk to configuration file.
    :param slave_nodes: Command to be executed
        :return: None

    """
    for slave_vms in slave_nodes:
        #get disk name from slave
        _, stdout, stderr = slave_vms.ssh_conn.execute_command("ls /dev/sd*[a-z]")
        disk = ""
        print(stdout, stderr)

        config = configparser.RawConfigParser()
        config.add_section('Global')
        config.set('Global', 'blocksize', '128k')
        config.set('Global', 'readwrite', 'write')
        config.set('Global', 'size', '512mb')
        config.set('Global', 'log_avg_msec', '5000')
        config.set('Global', 'iodepth', '16')
        config.set('Global', 'numjobs', '3')
        config.set('Global', 'direct', '0')
        config.set('Global', 'runtime', '120')
        for dev in stdout:
             if b"/dev/sda" in i:
                 pass
             elif b"/dev/sr0" in i:
                 pass
             else:
                disk = i.decode(encoding='UTF-8',errors='strict')
                print("disk=", disk)
                sec = 'job_' + disk
                config.add_section(sec)
                config.set(sec, 'filename', disk)
                config.set(sec, 'write_bw_log', 'job_' + disk)
                config.set(sec, 'write_lat_log', 'job_'+ disk)
                config.set(sec, 'write_iops_log', 'job_'+ disk)

        with open('test_fio.fio', 'w') as configfile:
            config.write(configfile)
    return None

def main():
    """
    """
    for i in range(config.SLAVE_VM_COUNT):
        #search if vm is already present
        data = search_vm(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, (config.VM_NAME+str(i)))
        if data:
            #stop the vm
            stop_vm(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                config.OVIRT_ENGINE_PASS, (config.VM_NAME+str(i)))
            #remove vm
            remove_vm(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                config.OVIRT_ENGINE_PASS, (config.VM_NAME+str(i))) 
    
    #create vm from template
    vms = create_vm_from_template(
            config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, config.CLUSTER_NAME, config.TEMPLATE_NAME,
            config.TEMPLATE_DS, config.VM_NAME, vm_count=config.SLAVE_VM_COUNT)

    # vms = get_vm_ip()
    #vms = ['192.168.105.18']
    if not vms:
        print("Not getting vm ip")
        sys.exit()
 
    print (vms)
    #create ssh session to vm and stop firewalld 
    linux_node = []
    for vm in vms:
        ln = Linux(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
        check_firewalld(ln)
        linux_node.append(ln)
    
    master_node = Linux(config.IOMETER_SERVER, config.IOMETER_UNAME, config.IOMETER_PASSWD)
    
    #add disk to vm
    for i in range(config.SLAVE_VM_COUNT): 
        vm_add_disk(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, config.TEMPLATE_DS, (config.VM_NAME+str(i)), config.DISK_NAME)

    configuration_file(linux_node)
    this_server = get_master_ip()
    start_iometer(linux_node, this_server)    
main()


