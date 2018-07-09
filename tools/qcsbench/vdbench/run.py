import time
import subprocess
import config

from nodes.node import Linux
from libs.ovirt_engine import create_vm_from_template, get_vm_ip, search_vm, stop_vm, remove_vm
from libs.vdb_config import create_config

NFS_SERVER = '192.168.102.13'
VDBENCH_MOUNT_LOCATION = '/var/vdbench_share'

def vdbench_deploy(node, repository=None):
    vdbench_dir = '/opt/vdbench'
    exe = 'vdbench'
    vdbench_exe = '{}{}{}'.format(vdbench_dir, node.path_seperator(), exe)
    mnt_dir = '/mnt/dir'
    if not repository:
        repository = '{}:{}'.format(NFS_SERVER, VDBENCH_MOUNT_LOCATION)
    mount_cmd = ['mount', repository, mnt_dir]
    _, res, error = node.ssh_conn.execute_command(['java', '-version'])
    if error:
        print (error)
        if not any(b"openjdk version" in line for line in error):
            print("deploying Java...............")
            node.deploy('java')
    if node.is_path_exists(vdbench_exe):
        print("vdbench present already ........")
        return vdbench_exe
    for _dir in (vdbench_dir, mnt_dir):
        node.makedir(_dir)
    print("fetching vdbench and deploying .......")
    node.deploy('nfs-utils')
    _, _, error = node.ssh_conn.execute_command(mount_cmd)
    for base, _dir, files in node.walk(mnt_dir):
        if exe in files:
            base_dir = '{}/*'.format(base)
            node.ssh_conn.execute_command(['cp', '-rp', base_dir, vdbench_dir])
            time.sleep(20)
            _, _, error = node.ssh_conn.execute_command(['umount', mnt_dir])
            print(error)
            return vdbench_exe


def key_is_present(node):
    """
    Verify the key is present
    """
    _, stdout, stderr =  node.ssh_conn.execute_command('ls /root/.ssh')
    if 'id_rsa.pub' in stdout:
        return True
    return False

def push_key_to_slave(master_node, slave_vms):
    """
    Copy public key of master to slave VMs
    """
    command = 'cat /root/.ssh/id_rsa.pub'
    _, stdout, stderr = master_node.ssh_conn.execute_command(command)
    key_data = stdout[0]
    for slave_node in slave_vms:
        command = 'echo {} >> /root/.ssh/authorized_keys'.format(key_data)
        _, stdout, stderr = slave_node.ssh_conn.execute_command(command)

def generate_key(master_node):
    """
    Genrate key
    """
    if key_is_present(master_node):
        print("A key is already present.")
    else:
        # Genarate private key
        master_node.ssh_conn.execute_command(
                        'echo y | ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -P ""')

def check_firewalld(master_node):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = master_node.ssh_conn.execute_command("firewall-cmd --state")
        if stderr and b"not" in stderr[0]:
            print("Firewall not running ...")
        else:
            command = "systemctl stop firewalld"
            _, stdout, stderr = master_node.ssh_conn.execute_command(command)
            print("Warning : Firewall is stopped, please start the firewall\
                   once execution is complete...")
    except Exception as e:
        print("Something goes wrong")

def configure_master(master_node, slave_nodes):
    """
    This will copy master ssh key to all the slave VM's for
    password less authentication.
    """
    check_firewalld(master_node)
    if key_is_present(master_node):
        push_key_to_slave(master_node, slave_nodes)
    else:
        generate_key(master_node)
        push_key_to_slave(master_node, slave_nodes)


def get_master_ip():
    """
    Gets IP of current machine
    """
    return subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)

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
    #vms = ['192.168.105.19']

    print(vms)
    linux_node = []
    for vm in vms:
        ln = Linux(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
        vdbench_exe = vdbench_deploy(ln)
        linux_node.append(ln)
    master_ip = get_master_ip()
    master_node = Linux(master_ip, config.MASTER_UNAME, config.MASTER_PASSWD)
    vdbench_exe = vdbench_deploy(master_node)
    configure_master(master_node, linux_node)
    vdbench_conf = create_config(config.SAMPLE_VDB_CONFIG, res_param='hd=',
                                 hostname=vms)
    print(vdbench_conf)
    print(vdbench_exe)
    vdbench_output = "/root/automation/qcs-automation/tools/qcsbench/vdbench/output"
    vdbench_cmd = '{} -f {} -o {}'.format(vdbench_exe, vdbench_conf, vdbench_output)
    print(vdbench_cmd)
    stdin, res, error = master_node.ssh_conn.execute_command(vdbench_cmd)

main()
