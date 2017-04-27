#!/bin/bash

echo -e ">>> Current memory is:"
echo "------------------------------------------------------------------------------"
free -m | egrep "(total|Mem)"
# modprobe acpi_memhotplug

echo -e "\n>>> Starting memory hot add..."
for mem_state in $(grep -l offline /sys/devices/system/memory/memory*/state ); do 
    echo online > $mem_state
done

echo -e "\n>>> Current memory is:"
echo "------------------------------------------------------------------------------"
free -m | egrep "(total|Mem)"
