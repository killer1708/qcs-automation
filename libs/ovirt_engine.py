#!/usr/bin/env python
"""
ovirt_engine.py: Used to perform ovirt engine operations using ovirt sdk.
"""

# from python lib
import logging
import time
import spur
import re
import sys

# from external lib
import ovirtsdk4 as sdk
import ovirtsdk4.types as types

# from qcs-atomation libs
from libs.log.logger import Log

log = Log()


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

def add_host(hosts_service, host_name, description, address, root_password,
             cluster, wait_for_up):
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

class OvirtEngine:
    """
    OvirtEngine operations using ovirt sdk
    """
    def __init__(self, ovirt_engine_ip, username, password):
        """
        Establish connection with Ovirt Engine
        :param ovirt_engine_ip - IP of Ovirt Engine
        :param username - Ovirt Engine username
        :param password - Ovirt Engine password
        """
        # Create the connection to the server:
        self.connection = sdk.Connection(
            url='https://{}/ovirt-engine/api'.format(ovirt_engine_ip),
            username=username,
            password=password,
            # ca_file='ca.pem',
            insecure=True,
            debug=True,
            log=logging.getLogger('qcs')
            )

    def get_vm_ip(self, vm_name='qcs_vm0'):
        """
        :param vm_name - VM name
        :return IP of vm
        """
        log.info("Retrieving IP for vm {}".format(vm_name))
        vms_service = self.connection.system_service().vms_service()

        # Find the virtual machine:
        try:
            vm = vms_service.list(search='name=' + str(vm_name))[0]
        except Exception as e:
            print(" Error while searching VM {}".format(vm_name), e)
            raise

        # Locate the service that manages the virtual machine, as that is where
        # the action methods are defined:
        vm_service = vms_service.vm_service(vm.id)
        # Get devices list
        reported_devices = vm_service.reported_devices_service().list()

        all_address = []
        for device in reported_devices:
            for ip in device.ips:
                all_address.append(ip.address)

        for ip in all_address:
            if re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", ip):
                log.info("Found IP {} for VM {}".format(ip, vm_name))
                return ip
        log.error("Unable to find IP for VM {}".format(vm_name)) 

    def search_vm(self, vm_name):
        """
        :param vm_name - name of vm to be searched
        :return - corresponding vm object
        """
        # Get the reference to the "vms" service:
        vms_service = self.connection.system_service().vms_service()

        # Use the "list" method of the "vms" service to search the virtual
        # machines that match a search query:
        vms = vms_service.list(
            search='name=%s'%vm_name,
            case_sensitive=False,
        )

        # Note that the format of the search query is the same that is
        # supported by the GUI search bar.

        # Print the virtual machine names and identifiers:
        for vm in vms:
            if vm.name == vm_name:
                return vm
        log.error("Unable to find vm {}".format(vm_name))

    def create_vm_from_template(self, cluster_name, template_name,
                                template_datastore, vm_name):
        """
        Create VM from the template.
        :param cluster_name - cluster name
        :param template_name - template name
        :param template_datastore - template datastore
        :param vm_name - vm name to be created
        :return: VM object 
        """

        # Get the reference to the root of the tree of services:
        system_service = self.connection.system_service()

        # Get the reference to the data centers service:
        dcs_service = self.connection.system_service().data_centers_service()
        # Get the reference to the clusters service:
        clusters_service = self.connection.system_service().clusters_service()
        # Get the reference to the hosts service:
        hosts_service = self.connection.system_service().hosts_service()
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
        disk_attachments = self.connection.follow_link(
                                    template_service.get().disk_attachments)
        disk = disk_attachments[0].disk

        # Get the reference to the service that manages the virtual machines:
        vms_service = system_service.vms_service()

        # Add a new virtual machine explicitly indicating the identifier of the
        # template version that we want to use and indicating that template
        # disk should be created on specific storage domain for the virtual
        # machine.
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
        return vm

    def stop_vm(self, vm_name):
        """
        :param vm_name - Name of VM
        :return None
        """
        # Get the reference to the "vms" service:
        vms_service = self.connection.system_service().vms_service()

        # Find the virtual machine:
        vm = vms_service.list(search='name=%s'%vm_name)[0]

        # Locate the service that manages the virtual machine, as that is where
        # the action methods are defined:
        vm_service = vms_service.vm_service(vm.id)

        # Call the "stop" method of the service to stop it:
        vm_service.stop()

        # Wait till the virtual machine is down:
        while True:
            time.sleep(5)
            vm = vm_service.get()
            if vm.status == types.VmStatus.DOWN:
                log.info("Successfully stopped vm {}".format(vm_name))
                break

    def remove_vm(self, vm_name):
        """
        :param vm_name - Name of VM
        :return None
        """
        # Find the service that manages VMs:
        vms_service = self.connection.system_service().vms_service()

        # Find the VM:
        vm = vms_service.list(search='name=%s'%vm_name)[0]

        # Note that the "vm" variable that we assigned above contains only the
        # data of the VM, it doesn't have any method like "remove". Methods are
        # defined in the services. So now that we have the description of the
        # VM we can find the service that manages it, calling the locator
        # method "vm_service" defined in the "vms" service. This locator method
        # receives as parameter the identifier of the VM and retursn a
        # reference to the service that manages that VM.
        vm_service = vms_service.vm_service(vm.id)

        # Now that we have the reference to the service that manages the VM we
        # can use it to remove the VM. Note that this method doesn't need any
        # parameter, as the identifier of the VM is already known by the
        # service that we located in the previous step.
        vm_service.remove()
        log.info("Successfully removed vm {}".format(vm_name))

    def add_disk(self, vm_name, disk_name, disk_size_gb, datastore):
        """
        Add disk to a VM
        :param vm_name - VM name
        :param disk_name - disk name to be used
        :param disk_size_gb - disk size in GB
        :param datastore - datastore to be used
        :return None
        """
        # Locate the virtual machines service and use it to find the virtual
        # machine:
        vms_service = self.connection.system_service().vms_service()
        vm = vms_service.list(search='name=%s'%vm_name)[0]

        # Locate the service that manages the disk attachments of the virtual
        # machine:
        disk_attachments_service = vms_service.vm_service(vm.id)\
                                       .disk_attachments_service()

        # Use the "add" method of the disk attachments service to add the disk.
        # Note that the size of the disk, the `provisioned_size` attribute, is
        # specified in bytes, so to create a disk of 10 GiB the value should
        # be 10 * 2^30.
        disk_attachment = disk_attachments_service.add(
            types.DiskAttachment(
                disk=types.Disk(
                    name='%s'%disk_name,
                    description='%s'%disk_name,
                    format=types.DiskFormat.COW,
                    provisioned_size=disk_size_gb * 2**30,
                    storage_domains=[
                        types.StorageDomain(
                           name='%s'%datastore,
                        ),
                    ],
                ),
                interface=types.DiskInterface.VIRTIO_SCSI,
                bootable=False,
                active=True,
            ),
        )

        # Wait till the disk is OK:
        disks_service = self.connection.system_service().disks_service()
        disk_service = disks_service.disk_service(disk_attachment.disk.id)
        while True:
            time.sleep(5)
            disk = disk_service.get()
            if disk.status == types.DiskStatus.OK:
                log.info("Successfully added disk {} to vm {} of size {} GB"\
                         .format(disk_name, vm_name, disk_size_gb))
                break

    def create_vm_from_template(self, vm_name, cluster_name, template_name,
                                template_datastore):
        """
        Create VM from the template.
        :param cluster_name - cluster name
        :param template_name - template name
        :param template_datastore - template datastore
        :param vm_name - vm name to be created
        :param vm_count - number of vms to be created
        :return: VM object
        """
        # Get the reference to the root of the tree of services:
        system_service = self.connection.system_service()

        # Get the reference to the data centers service:
        dcs_service = self.connection.system_service().data_centers_service()
        # Get the reference to the clusters service:
        clusters_service = self.connection.system_service().clusters_service()
        # Get the reference to the hosts service:
        hosts_service = self.connection.system_service().hosts_service()
        # Get the reference to the service that manages the storage domains:
        storage_domains_service = system_service.storage_domains_service()

        # Find the storage domain we want to be used for virtual machine disks:
        #import pdb; pdb.set_trace()
        storage_domain = storage_domains_service.list(
                             search="name={}".format(template_datastore))[0]

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
        disk_attachments = self.connection.follow_link(
                                    template_service.get().disk_attachments)
        disk = disk_attachments[0].disk

        # Get the reference to the service that manages the virtual machines:
        vms_service = system_service.vms_service()

        # Add a new virtual machine explicitly indicating the identifier of the
        # template version that we want to use and indicating that template
        # disk should be created on specific storage domain for the virtual
        # machine.
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

        # Wait till the virtual machine is down, which indicates that all the
        # disks have been created:
        while True:
            time.sleep(5)
            vm = vm_service.get()
            if vm.status == types.VmStatus.DOWN:
                vm_service.start()
                while vm_service.get().status != types.VmStatus.UP:
                    continue
                log.info("Successfully created VM {} on datastore {}"\
                         .format(vm_name, template_datastore))
                break
        return vm

    def close_connection(self):
        """
        Close Ovirt Engine connection
        """
        self.connection.close()


if __name__ == '__main__':
    print("Module loaded successfully.")
    # add_dc('dc_service', '', 'My data center', False, 4, 0)
    # add_cluster('cl_service', '', 'My cluster', 'Intel Family', 'mydc')
    
