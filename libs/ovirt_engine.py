#!/usr/bin/env python

import logging
import time
import spur
import libs.config as config

import ovirtsdk4 as sdk
import ovirtsdk4.types as types

FTP_SERVER = '192.168.102.13'
FTP_USERNAME = 'root'
FTP_PASSWORD = 'master#123'


def track_status(service, final_status, status_check_sleep):
    while True:
        time.sleep(status_check_sleep)
        tracking_object = service.get()
        if tracking_object.status == final_status:
            break


def add_dc(dcs_service, dc_name, description, local, major, minor):
    """
    Create Datacenter on the ovirt engine
    :param dcs_service: Datacenter service object
    :param dc_name: Datacenter Name
    :param description: Description
    :param local:
    :param major:
    :param minor:
    :return:
    """
    dc = dcs_service.add(
        types.DataCenter(
            name=dc_name,
            description=description,
            local=local,
            version=types.Version(major=major,minor=minor),
        ),
    )


def add_cluster(cluster_service, cl_name, description, cltype, dc):
    """
    Create cluster.
    :param cluster_service: cluster service object
    :param cl_name: Cluster name
    :param description: description
    :param cltype: type
    :param dc: Datacenter
    :return:
    """
    cluster_service.add(
        types.Cluster(
            name=cl_name,
            description=description,
            cpu=types.Cpu(
                architecture=types.Architecture.X86_64,
                type=cltype,
            ),
            data_center=types.DataCenter(
                name=dc,
            ),
        ),
)


def add_host(hosts_service, host_name, description, address, root_password, cluster, wait_for_up):
    print('Adding Host : ' + host_name + '...')
    host = hosts_service.add(
        types.Host(
            name=host_name,
            description=description,
            address=address,
            root_password=root_password,
            cluster=types.Cluster(
                name=cluster,
            ),
        ),
    )
    if wait_for_up:
        host_service = hosts_service.host_service(host.id)
        track_status(host_service, types.HostStatus.UP, 1)


def get_vm_ip(qnap_vm_file):
    """
    Connect to server and return the IP's by reading the file
    :param qnap_vm_file: FTP file name
    :return: list of IP's
    """
    try:
        ssh_shell = spur.SshShell(FTP_SERVER, username=FTP_USERNAME,
                                  password=FTP_PASSWORD,
				  missing_host_key=spur.ssh.MissingHostKey.accept)
        with ssh_shell.open(qnap_vm_file, 'rb') as remote:
            return remote.read().splitlines()
    except IOError as e:
        pass


def create_vm_from_template(cluster_name, template_name, template_datastore,
                            vm_name=None, vm_count=1):
    """
    Create VM from the template.
    :param cluster_name: cluster name
    :param template_name: template name
    :param template_datastore: template datastore
    :param vm_name: vm name to be created
    :param ip: Not Supported
    :return: VM IP list
    """

    logging.basicConfig(level=logging.DEBUG, filename='example.log')
    clean_and_backup_ip_server(config.VM_IP_RECORDS)

    # Create the connection to the server:
    conn = sdk.Connection(
        url='https://{}/ovirt-engine/api'.format(config.OVIRT_ENGINE_IP),
        username=config.OVIRT_ENGINE_UNAME,
        password=config.OVIRT_ENGINE_PASS,
        # ca_file='ca.pem',
        insecure=True,
        debug=True,
        log=logging.getLogger(),
    )
    connection = conn

    for count in range(vm_count):
        # Get the reference to the root of the tree of services:
        system_service = connection.system_service()

        # Get the reference to the data centers service:
        dcs_service = connection.system_service().data_centers_service()
        # Get the reference to the clusters service:
        clusters_service = connection.system_service().clusters_service()
        # Get the reference to the hosts service:
        hosts_service = connection.system_service().hosts_service()
        # Get the reference to the service that manages the storage domains:
        storage_domains_service = system_service.storage_domains_service()

        # Find the storage domain we want to be used for virtual machine disks:
        storage_domain = storage_domains_service.list(
                                        search='name=%s'% template_datastore)[0]

        # Get the reference to the service that manages the templates:
        templates_service = system_service.templates_service()

        templates = templates_service.list(search='name=%s' %template_name)
        template_id = None
        for template in templates:
            if template.version.version_number == 1:
                template_id = template.id
                break

        # Find the template disk we want be created on specific storage domain
        # for our virtual machine:
        template_service = templates_service.template_service(template_id)
        disk_attachments = connection.follow_link(
                                    template_service.get().disk_attachments)
        disk = disk_attachments[0].disk

        # Get the reference to the service that manages the virtual machines:
        vms_service = system_service.vms_service()

        # Add a new virtual machine explicitly indicating the identifier of the
        # template version that we want to use and indicating that template disk
        # should be created on specific storage domain for the virtual machine:
        vm = vms_service.add(
            types.Vm(
                name=vm_name + str(count),
                cluster=types.Cluster(
                    name=cluster_name
                ),
                template=types.Template(
                    id=template_id
                ),
                disk_attachments=[
                    types.DiskAttachment(
                        disk=types.Disk(
                            id=disk.id,
                            format=types.DiskFormat.COW,
                            storage_domains=[
                                types.StorageDomain(
                                    id=storage_domain.id,
                                ),
                            ],
                        ),
                    ),
                ],
                 )
        )
        # Get a reference to the service that manages the virtual machine that
        # was created in the previous step:
        vm_service = vms_service.vm_service(vm.id)

        # Wait till the virtual machine is down, which indicates that all the
        # disks have been created:
        while True:
            time.sleep(5)
            vm = vm_service.get()
            if vm.status == types.VmStatus.DOWN:
                vm_service.start()
                while vm_service.get().status != types.VmStatus.UP:
                    continue
                break

    connection.close()
    vm_ips = get_vm_ip(config.VM_IP_RECORDS)
    return vm_ips


def clean_and_backup_ip_server(records_file):
    """
    Clear the record file and take backup
    :param records_file: Backup file path
    :return:
    """
    try:
        ssh_shell = spur.SshShell(FTP_SERVER, username=FTP_USERNAME,
                                  password=FTP_PASSWORD,
				  missing_host_key=spur.ssh.MissingHostKey.accept)
        with ssh_shell.open(config.QCS_AUTOMATION_MASTER_CONF, 'a') as records,\
                ssh_shell.open(records_file, 'rb') as orig:
            records.write(str(orig.read()))
            ssh_shell.run(['rm', '-f', '{}'.format(records_file)])
    except IOError as e:
        pass

if __name__ == '__main__':
    # add_dc('dc_service', '', 'My data center', False, 4, 0)
    # add_cluster('cl_service', '', 'My cluster', 'Intel Family', 'mydc')
    create_vm_from_template(config.CLUSTER_NAME, config.TEMPLATE_NAME,
                            config.TEMPLATE_DS, 'automation-vm-test')
