#!/usr/bin/env python
"""
run.py: Execute vdbench test as per config.py
"""

# from python lib
import os
import sys
import time
import subprocess
import tempfile

# from qcs-automation libs
from nodes.node import Linux
from libs.vdb_config import create_config
from libs.ovirt_engine import (create_vm_from_template,
                               get_vm_ip,
                               search_vm,
                               stop_vm,
                               remove_vm)
from libs.log.logger import Log
from tools.qcsbench.vdbench import config

# create log object
log = None
if os.environ.get('USE_ROBOT_LOGGER', None) == "True":
    from lib.log.logger import Log
    log = Log()
else:
    log = Log()

NFS_SERVER = '192.168.102.13'
VDBENCH_MOUNT_LOCATION = '/var/vdbench_share'
VDBENCH_EXE_LOC = "/opt/vdbench"
VDBENCH_LOGS = "/opt/vdbench/output_dir"
WIN_VDBENCH_EXE_LOC = "c:\\vdbench"
WIN_VDBENCH_LOGS = "c:\\vdbench\\output_dir"


def vdbench_deploy(host):
    """
    Deploy vdbench on a host
    :param host - host where vdbench need to be deployed
    :return None
    """
    if host.host_type == 'linux':
        vdbench_exe = "{}/vdbench".format(VDBENCH_EXE_LOC)
        # check vdbench
        log.info("Check if vdbench already present")
        if host.is_path_exists(vdbench_exe):
            log.info("vdbench exe already present on host {}".format(host))
            return
        # check java & deploy if not available
        log.info("Verify if java alredy presnt")
        status, output, error = host.ssh_conn.execute_command(['java', '-version'])
        if status:
            log.info(output)
            log.error(error)
            sys.exit(1)
        else:
            log.info("java already present on host {}".format(host))
        if not any("openjdk version" in line for line in error):
            log.info("Deploying Java on host {}".format(host))
            host.deploy('java')
        # copy vdbench source files to the host
        log.info("Copying vdbench source files to host {}".format(host))
        host.ssh_conn.scp_put(localpath=VDBENCH_EXE_LOC,
                              remotepath=os.path.dirname(VDBENCH_EXE_LOC),
                              recursive=True)
        log.info("Successfully copied vdbench source files to host {}".format(host))
    elif host.host_type == 'windows':
        # vdbench_exe = "{}\\vdbench.bat".format(WIN_VDBENCH_EXE_LOC)
        pass
    """
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
    """

def key_is_present(node):
    """
    Verify the key is present
    """
    _, stdout, stderr =  node.ssh_conn.execute_command('ls /root/.ssh')
    if 'id_rsa.pub' in stdout[0]:
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
        status, stdout, stderr = slave_node.ssh_conn.execute_command(command)
        if status:
            log.info(stdout)
            log.error(stderr)

def generate_key(master_node):
    """
    Genrate key
    """
    # Genarate private key
    master_node.ssh_conn.execute_command(
                        'echo y | ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -P ""')

def check_firewalld(master_node):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = master_node.ssh_conn.execute_command("firewall-cmd --state")
        if stderr and 'not' in stderr[0]:
            log.info("Firewall is not running")
        else:
            command = 'systemctl stop firewalld'
            _, stdout, stderr = master_node.ssh_conn.execute_command(command)
            log.warn("Firewall is stopped, please start the firewall +\
                      once execution completes")
    except Exception as e:
        print("Something goes wrong")

def configure_master_host(master_node, slave_nodes):
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


def get_current_host_ip():
    """
    Gets IP of current machine
    """
    out = subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)
    ip = out.decode('utf-8').splitlines()[0]
    return ip

def generate_paramfile(load_type, hosts, conf):
    block_io = False
    file_io = False

    # Check for file/block IO
    if load_type.lower() == 'block_io':
        block_io = True
    elif load_type.lower() == 'file_io':
        file_io = True

    if block_io:
        newconf = list() 
        i = 1
        sd_params = []
        for host in hosts:
            # add hd params
            hd_params = "hd={},shell=ssh,system={},user=root,vdbench={}"\
                .format(str(host),
                        str(host),
                        VDBENCH_EXE_LOC)
            newconf.append(hd_params)

            # terminate if no disk found for a host
            if not host.disks:
                log.info("Disks are: {}".format(host.disks))
                raise Exception("No disks found for host {}".format(
                    str(host)))
            for disk in host.disks:
                if conf.get('sd_params'):
                    temp = []
                    for key, value in conf['sd_params'].items():
                        temp.append("{}={}".format(key, value))
                    params = "sd=sd_{},host={},lun={},{}".format(
                              i, str(host), disk, ','.join(temp))
                else:
                    params = "sd=sd_{},host={},lun={}".format(
                              i, str(host), disk)
                sd_params.append(params)
                # increment i
                i += 1
            # disk for loop ends here

        wd_params = []
        for sd_line in sd_params:
            sd = sd_line.split(',')[0].split('=')[1]
            if conf.get('wd_params'):
                temp = []
                for key, value in conf['wd_params'].items():
                    temp.append("{}={}".format(key, value))
                params = "wd=wd_{},sd={},{}".format(sd, sd, ','.join(temp))
            else:
                params = "wd=wd_{},sd={}".format(sd, sd)
            wd_params.append(params)

        if conf.get('rd_params'):
            temp = []
            for key, value in conf['rd_params'].items():
                temp.append("{}={}".format(key, value))
            params = "rd=rd1,wd=*,{}".format(','.join(temp))
        else:
            params = "rd=rd1,wd=*"
        rd_params = [params]

        # add all params
        all_params = sd_params + wd_params + rd_params
        newconf.extend(all_params)

    # block io config generation end here

    if file_io:
        # TBD
        raise NotImplementedError()

    temp_paramfile = tempfile.NamedTemporaryFile(delete=False).name
    with open(temp_paramfile, 'w') as fh:
        for line in newconf:
            fh.write(line+"\n")
    return temp_paramfile

def main():
    """
    Standalone vdbench execution steps:
    precondition: update config.py as per need
    1. create vms
    2. add disks
    3. choose file/block IO
    4. start vdbench load in foreground
    """
    log_dir = "output"
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, "vdbench_stdout.log")
    log.initialise(logfile, config.LOG_LEVEL)
    print("Logs will be collected in '{}' directory".format(log_dir))
    print("logfile: {}".format(logfile))
    log.info("Remove existing vms if any")
    for i in range(config.SLAVE_VM_COUNT):
        # search if vm is already present
        data = search_vm(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, (config.VM_NAME+str(i)))
        if data:
            # stop the vm
            stop_vm(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                config.OVIRT_ENGINE_PASS, (config.VM_NAME+str(i)))
            # remove vm
            remove_vm(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                config.OVIRT_ENGINE_PASS, (config.VM_NAME+str(i)))

    log.info("Step 1. Create VM(s)")
    vms = create_vm_from_template(
            config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
            config.OVIRT_ENGINE_PASS, config.CLUSTER_NAME, config.TEMPLATE_NAME,
            config.TEMPLATE_DS, config.VM_NAME, vm_count=config.SLAVE_VM_COUNT)

    log.info("VM IPs are: {}".format(vms))
    if not vms:
        log.critical("No vm IP found")
        sys.exit(1)

    log.info("Creating host objects") 
    host_list = list()
    for vm in vms:
        if config.HOST_TYPE.lower() == 'linux':
            host = Linux(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
        elif config.HOST_TYPE.lower() == 'windows':
            # host = Windows(vm, config.SLAVE_UNAME, config.SLAVE_PASSWORD)
            pass
        else:
            log.error("Unknown host type - {}".format(config.HOST_TYPE))
        # update available disks
        host_list.append(host)
    # get master host
    master_host = host_list[0]
    log.info("Step 2. Add disk to VM(s)")
    log.info("Deploy vdbench on all the hosts")
    for host in host_list:
        for _ in range(config.DISK_COUNT):
            host.add_disk(config.DISK_SIZE)
        vdbench_deploy(host)
        host.refresh_disk_list()
        host.change_hostname()

    log.info("Disks are: {}".format(host.disk_list))
    log.info("Configure master host and copy master ssh keys to all slaves")
    configure_master_host(master_host, host_list)
    # create vdbench temp paramfile based upon load type
    log.info("Step 3. Create vdbench temp paramfile based upon load type")
    temp_paramfile = generate_paramfile(config.LOAD_TYPE, host_list,
                                        config.WORKLOAD_INFO)
    log.info(temp_paramfile)
    # copy parameter file to master host
    master_host.ssh_conn.scp_put(localpath=temp_paramfile,
                                 remotepath=VDBENCH_EXE_LOC)
    if master_host.host_type == 'linux': 
        paramfile = "{}/{}".format(VDBENCH_EXE_LOC,
                                   os.path.basename(temp_paramfile))
        vdbench_exe = VDBENCH_EXE_LOC + "/vdbench"
        logdir = "{}/output".format(VDBENCH_EXE_LOC)
    else:
        paramfile = "{}/{}".format(WIN_VDBENCH_EXE_LOC,
                                   os.path.basename(temp_paramfile))
        vdbench_exe = WIN_VDBENCH_EXE_LOC + "\\vdbench.bat"
        logdir = "{}\\output".format(VDBENCH_EXE_LOC)
    # remove templfile created
    os.unlink(temp_paramfile)
    # prepare vdbench command
    cmd = '{} -f {} -o {}'.format(vdbench_exe, paramfile, logdir)
    log.info("Step 4. Start the vdbench workload")
    status, stdout, stderr = master_host.ssh_conn.execute_command(cmd)
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("VDBench completed successfully.")
    # Collect logs
    log_dir = os.path.join(log_dir, str(master_host))
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    master_host.ssh_conn.scp_get(remotepath=logdir,
                                 localpath=log_dir, recursive=True)
    log.info("Collected vdbench logs into {}".format(log_dir))
    # Cleanup paramfile from master host
    log.info("Cleaning up paramfile on master host")
    cmd = "rm -f {}".format(paramfile)
    _, _, _ = master_host.ssh_conn.execute_command(cmd)


if __name__ == '__main__':
    main()

