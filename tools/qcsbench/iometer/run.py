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

def start_iometer(master, slave_nodes, server):
    """
    Start Dynamo on slave nodes and iometer on client node
    :param master: ssh connection iometer server(windows)
    :param slave_nodes: ssh connection to slave nodes(linux)
    :param server: ip of the current machine
        :return: None

    """
    for slave_vms in slave_nodes:
         #copy dynamo on slave machine
         slave_vms.ssh_conn.copy_command(config.LOCAL_PATH, config.REMOTE_PATH)
         slave_vms.ssh_conn.execute_command('chmod +x %s' %config.REMOTE_PATH)
         #start dynamo on slave machine
         _, stdout, stderr = slave_vms.ssh_conn.execute_command("nohup /root/dynamo -i '{0}'\
                             -m '{1}' > /dev/null 2>&1 &\n".format(master.ip, slave_vms.ip))
         print("Dynamo start on client {}".format(slave_vms.ip))

    # remove if existing config and result file on master node
    _, stdout, stderr = master.ssh_conn.execute_command("cmd \/c del /f {0}result.csv"\
                        .format(config.IOMETER_SDK))
    _, stdout, stderr = master.ssh_conn.execute_command("cmd \/c del /f {0}{1}"\
                        .format(config.IOMETER_SDK, config.IOMETER_CONFIG_FILE))

    #copy iometer configuration file on iometer server
    _, stdout, stderr = master.ssh_conn.execute_command("cmd \/c echo y | pscp.exe -pw {1} \
                        root@{0}:{2} {3}".format(server, config.MASTER_PASSWD,\
                         config.IOMETER_CONFIG_FILE, config.IOMETER_SDK)) 
    print(stdout,stderr)

    #start iometer on master node
    _, stdout, stderr = master.ssh_conn.execute_command("cmd \/c {0}IOmeter.exe \
                        /c {0}test_iometer.icf /r {0}result.csv".format(config.IOMETER_SDK))   
    #copy result file into output dir
    _, stdout, stderr = master.ssh_conn.execute_command("cmd \/c echo y | pscp.exe -pw {1} \
                        {3}result.csv root@{0}:{2}".format(server, config.MASTER_PASSWD,\
                         config.IOMETER_OUTPUT_DIR, config.IOMETER_SDK)) 
    return None

def configuration_file(slave_nodes):
    """
    Add the number of slave client and disk to configuration file.
    :param slave_nodes: Command to be executed
        :return: None

    """
    for slave_vms in slave_nodes:
         #get disk name from slave
         _, stdout, stderr = slave_vms.ssh_conn.execute_command("lsblk -d -n -oNAME | awk {'print $1'}")
         disk = ""
         print(stdout, stderr)
         for i in stdout:
             if b"sda" in i:
                 pass
             elif b"sr0" in i:
                 pass
             else:
                 disk = i.decode(encoding='UTF-8',errors='strict')
                 print("disk=", disk)

         flag = False
         #write disk name and ip address to config file
         with open("iometer.icf") as fd:
             with open(config.IOMETER_CONFIG_FILE, "w") as fd1:
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
    print(this_server)
    start_iometer(master_node, linux_node, this_server)    
main()


