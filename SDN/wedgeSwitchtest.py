from cumulus import CumulusDriver
from napalm import get_network_driver

cumulus_driver = CumulusDriver('192.168.30.34','cumulus','CumulusLinux!')
#driver = get_network_driver(cumulus_driver)
with cumulus_driver.open() as device:
    print(device.get_facts())
    print(driver.get_interface_counters())

