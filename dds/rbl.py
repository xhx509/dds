import serial


def main():
    sp = serial.Serial()
    sp.baudrate = 19200
    sp.timeout = 1
    sp.port = '/dev/ttyUSB0'
    sp.open()

    sp.write(b'AT\r')
    rv = sp.readall()
    print(rv)

    sp.write(b'AT-MSSTM\r')
    rv = sp.readall()
    print(rv)

    sp.write(b'AT+CGSN\r')
    rv = sp.readall()
    print(rv)

    sp.close()


if __name__ == '__main__':
    main()
