#!/usr/bin/env python

import logging
import time
import spur

import ovirtsdk4 as sdk
import ovirtsdk4.types as types
IP_SERVER = '192.168.102.13'
USERNAME = 'root'
PASSWORD = 'master#123'

def get_vm_ip():
    '''
    Connect to server and return the IP's by reading the file
    :return: list of IP's
    '''
    ssh_shell = spur.SshShell(IP_SERVER, username=USERNAME, password=PASSWORD)
    with ssh_shell.open('/qnap-vm.txt', 'rb') as remote:
        return remote.read().splitlines()


def create_vm_from_template(cluster_name, template_name, template_datastore, vm_name=None, ip=None):
    logging.basicConfig(level=logging.DEBUG, filename='example.log')

    # Create the connection to the server:
    conn = sdk.Connection(
        url='https://192.168.103.39/ovirt-engine/api',
        username='admin@internal',
        password='master@123',
        # ca_file='ca.pem',
        insecure=True,
        debug=True,
        log=logging.getLogger(),
    )
    connection = conn
    # Get the reference to the root of the tree of services:
    system_service = connection.system_service()

    # Get the reference to the service that manages the storage domains:
    storage_domains_service = system_service.storage_domains_service()

    # Find the storage domain we want to be used for virtual machine disks:
    storage_domain = storage_domains_service.list(search='name=%s'% template_datastore)[0]

    # Get the reference to the service that manages the templates:
    templates_service = system_service.templates_service()

    # When a template has multiple versions they all have the same name, so
    # we need to explicitly find the one that has the version name or
    # version number that we want to use. In this case we want to use
    # version 3 of the template.
    templates = templates_service.list(search='name=%s' %template_name)
    template_id = None
    import ipdb; ipdb.set_trace()
    for template in templates:
        if template.version.version_number == 1:
            template_id = template.id
            break

    # Find the template disk we want be created on specific storage domain
    # for our virtual machine:
    template_service = templates_service.template_service(template_id)
    disk_attachments = connection.follow_link(template_service.get().disk_attachments)
    disk = disk_attachments[0].disk

    # Get the reference to the service that manages the virtual machines:
    vms_service = system_service.vms_service()

    # Add a new virtual machine explicitly indicating the identifier of the
    # template version that we want to use and indicating that template disk
    # should be created on specific storage domain for the virtual machine:
    vm = vms_service.add(
        types.Vm(
            name=vm_name,
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


    # Wait till the virtual machine is down, which indicats that all the
    # disks have been created:
    while True:
        time.sleep(5)
        vm = vm_service.get()
        if vm.status == types.VmStatus.DOWN:
            vm_service.start()
            break
    vm_ip_address = get_vm_ip()

    # Close the connection to the server:
    connection.close()
    return vm_ip_address

if __name__ == '__main__':
    for i in range(1):
        create_vm_from_template('newcl', 'automation-template', 'data1', 'trail_vm%s' %i)