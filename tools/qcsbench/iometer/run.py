import time
import subprocess
import config

from nodes.node import Linux
from libs.ovirt_engine import create_vm_from_template, get_vm_ip, vm_add_disk, remove_vm,search_vm, stop_vm
from libs.vdb_config import create_config

def check_firewalld(slave_node):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = slave_node.ssh_conn.execute_command("firewall-cmd --state")
        if stderr and b"not" in stderr[0]:
            print("Firewall not running ...")
        else:
            command = "systemctl stop firewalld"
            _, stdout, stderr = conn.execute_command(command)
            print("Warning : Firewall is stopped, please start the firewall\
                   once execution is complete...")
    except Exception as e:
        print("Something goes wrong")

def start_iometer(master, slave_nodes):
    """
    Start Dynamo on slave nodes and iometer on client node
    """
    for slave_vms in slave_nodes:
         slave_vms.ssh_conn.copy_command(config.LOCAL_PATH, config.REMOTE_PATH)
         slave_vms.ssh_conn.execute_command('chmod +x %s' %config.REMOTE_PATH)
         _, stdout, stderr = master_node.ssh_conn.execute_command("nohup /root/dynamo -i {}\
                                            -m {} > /dev/null 2>&1 &\n"%(master, slave_vms))
         master_node.ssh_conn.copy_command("/root/automation/qcs-automation/tools/qcsbench/iometer/test_iometer.icf",\
         "C:\\Users\\Administrator\\Desktop")
         print("Dynamo start on client {}".format(slave_vms)) 

    #start iometer on master node
    _, stdout, stderr = master_node.ssh_conn.execute_command("cmd \/c C:\\Users\\Administrator\\Desktop\\IOmeter.exe")   

def configuration_file(slave_nodes):
    """
    Add the number of slave client and disk to configuration file.
    """
    for slave_vms in slave_nodes:
         _, stdout, stderr = slave_vms.ssh_conn.execute_command("lsblk -d -n -oNAME | awk {'print $1'}")
         for i in stdout:
             if not b"sda" or b"sr0" in i:
                 disk = i.decode(encoding='UTF-8',errors='strict')
                 print(disk)
         flag = False
         with open("iometer.icf") as fd:
             with open("test_iometer.icf", "w") as fd1:
                 for line in fd:
                     if line.startswith("\'Manager network address"):
                         fd1.write(line)
                         flag = True
                         data = slave_vms.ip + "\n"
                     elif line.endswith("\'Target\n"):
                         fd1.write(line)
                         flag = True
                         data = disk + "\n"
                     elif flag:
                         fd1.write(data)
                         flag = False
                     else:
                         fd1.write(line)
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
    
    vms = create_vm_from_template(
            config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, config.CLUSTER_NAME, config.TEMPLATE_NAME,
            config.TEMPLATE_DS, config.VM_NAME, vm_count=config.SLAVE_VM_COUNT)

    #vms = get_vm_ip()
    #vms = ['192.168.105.18']
   
    print (vms)
    linux_node = []
    for vm in vms:
        ln = Linux(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
        check_firewalld(ln)
        linux_node.append(ln)
    master_node = Linux(config.IOMETER_SERVER, config.IOMETER_UNAME, config.IOMETER_PASSWD)

    for i in range(config.SLAVE_VM_COUNT): 
        vm_add_disk(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, config.TEMPLATE_DS, (config.VM_NAME+str(i)), config.DISK_NAME)

    configuration_file(linux_node)
    start_iometer(master_node, linux_node)

main()

