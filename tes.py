import tinytuya as ty

# ty.set_debug(True)

d = ty.OutletDevice('ebf19ba30ea9d231c5ega7', "192.168.100.11", "]apQZ4a3{]k;X+VW")
d.set_socketPersistent(True)
d.set_version(3.4)
d.turn_on()

print(d.status())