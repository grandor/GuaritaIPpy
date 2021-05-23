import binascii
import socket

from datetime import datetime
from typing import Generator

Hex_str = str


class GuaritaIP:
    def __init__(self, device_address: str, device_port: int, access_code: str,
                 default_timeout: int = 1):
        """Constructor method
        """
        self.d_address = device_address
        self.d_port = device_port
        self.access_code = access_code
        self.default_timeout = default_timeout

    def _add_checksum(self, input_hex: Hex_str) -> bytes:
        """Calculate the checksum, concatenate it to the end of 
        input_hex and return the value.

        :param input_hex: string representing a hexadecimal number.
        :type input_hex: str

        :return: *bytes* containing a hexadecimal number.
        :rtype: bytes
        """
        cs = sum([int(input_hex[i:i+2], 16) for i in range(0, 
                 len(input_hex), 2)])

        if cs > 255:
            cs = hex(cs)[-2:]
        else:
            cs = hex(cs).lstrip("0x")
        return binascii.a2b_hex(input_hex + cs.zfill(2))

    def _remove_extra_byte(self, input_hex: Hex_str) -> Hex_str:
        """Remove the extra byte 0x00 returned by firmware 2.005y
        of Multifuncao-4A.

        :param input_hex: string representing a hexadecimal number.
        :type input_hex: str

        :return: *str* representing a hexadecimal number.
        :rtype: str
        """
        if input_hex[:2] == input_hex[2:2] and input_hex[:2] == "00":
            return input_hex[2:]
        else:
            return input_hex
    
    def _bcdDigits(self, chars: tuple) -> Generator[str, None, None]:
        """Convert binary-coded decimals to decimal representation.

        :param chars: tuple containing bytes representing BCD.
        :type chars: tuple

        :return: *generator object*.
        :rtype: bcdDigits
        """
        for char in chars:
            char = ord(char)
            for val in (char >> 4, char & 0xF):
                if val == 0xF:
                    return
                yield str(val)

    def _toBCD(self, chars: tuple):
        # TODO

    def _send_to_device(self, message: bytes, response_size: int, 
                        conn_timeout: int) -> bytes:
        """Open a TCP connection to Modulo Guarita, send the message
        and close the connection.
        
        :param message: sequence of bytes representing the command.
        :type message: bytes
        :param response_size: number of bytes expected in response.
        :type response_size: int
        :param conn_timeout: number of seconds to wait for a response.
        :type conn_timeout: int

        :return: *bytes* containing the response or *False* on failure 
        to connect.
        :rtype: bytes
        """
        tcp_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dst = (self.d_address, self.d_port)
        tcp_conn.settimeout(conn_timeout)
        try:
            tcp_conn.connect(dst)
        except socket.timeout:
            return False
        if self.access_code:
            tcp_conn.send(self.access_code.encode("utf-8"))
            ac_response = tcp_conn.recv(12)
            if not ac_response:
                return False
        tcp_conn.send(message)
        response = tcp_conn.recv(response_size)
        tcp_conn.close()
        return response

    def write_id_str(self, which_row: int, row2: str, row3: str = "", 
                    timeout: int = 0) -> bool:
        """PC 1 and PC 2: Write identification (Rows 2 and 3 - Display).

        :param which_row: integer representing which row will be written
            (or both). 0 stands for both rows, 2 for row 2 and 3 for 
            row 3
        :type which_row: int
        :param row2: 20-character ASCII string
        :type row2: str
        :param row3: 20-character ASCII string
        :type row3: str, optional
        :param timeout: number of seconds to wait for a response, 
            defaults to 0 (and is overriden by 
            GuaritaIP.default_timeout)
        :type timeout: int, optional

        :return: *bytes* containing text.
        :rtype: bytes
        """
        if len(row2) > 20 or len(row3) > 20:
            return False
        if timeout == 0:
            timeout = self.default_timeout
        msg_row2 = '0001' + row2
        msg_row2 = self._add_checksum(msg_row2)
        if which_row == 0:
            msg_row3 = '0002' + row3
            msg_row3 = self._add_checksum(msg_row3)
            if (self._send_to_device(msg_row2, 3, timeout) == b'\x00\x01\x01' 
                and self._send_to_device(msg_row3, 3, timeout) 
                == b'\x00\x02\x02'):
                return True
            else:
                return False
        elif which_row == 2:
            if self._send_to_device(msg_row2, 3, timeout) == b'\x00\x01\x01':
                return True
            else:
                return False
        elif which_row == 3:
            msg_row3 = '0002' + row2
            msg_row3 = self._add_checksum(msg_row3)
            if self._send_to_device(msg_row3, 3, timeout) == b'\x00\x02\x02':
                return True
            else:
                return False
        else:
            return False

    def read_id_str(self, timeout: int = 0) -> bytes:
        """PC 3: Read identification (Rows 2 and 3 - Display).

        :param timeout: number of seconds to wait for a response, 
            defaults to 0 (and is overriden by 
            GuaritaIP.default_timeout)
        :type timeout: int, optional

        :return: *bytes* containing text.
        :rtype: bytes
        """
        if timeout == 0:
            timeout = self.default_timeout
        msg = b'\x00\x03\x03'
        return self._send_to_device(msg, 44, timeout)

    def write_datetime(self, input_datetime: datetime, 
                       timeout: int = 0) -> bool:
        if timeout == 0:
            timeout = self.default_timeout
        # terminar implementação
        msg = b'\x00\x0b'
        response = self._send_to_device(msg, 3, timeout)
        if response == b'\x00\x0b\x0b':
            return True
        else:
            return False

    def read_datetime(self, timeout: int = 0) -> datetime:
        """PC 12: Read date and time from Modulo Guarita.
        
        :param timeout: number of seconds to wait for a response, 
            defaults to 0 (and is overriden by 
            GuaritaIP.default_timeout)
        :type timeout: int, optional

        :return: *datetime* object containing current date and time from 
            device or *datetime* object 0001-01-01 00:00:00 on failure.
        :rtype: datetime
        """
        if timeout == 0:
            timeout = self.default_timeout
        msg = b'\x00\x0c\x0c'
        response = self._send_to_device(msg, 10, timeout)
        if response:
            response = list(str(response[2:8], 'utf_8'))
            response = list(self._bcdDigits(response))
            year = int('20' + ''.join(response[4:6]))
            month = int(''.join(response[2:4]))
            day = int(''.join(response[:2]))
            hour = int(''.join(response[6:8]))
            minute = int(''.join(response[8:10]))
            second = int(''.join(response[10:]))
            return datetime(year, month, day, hour, minute, second)
        else:
            return datetime(1,1,1)

    def reboot(self) -> bytes:
        """PC 18: Reboot Modulo Guarita (applies Ethernet config.).

        :return: *None*.
        :rtype: None
        """
        msg = b'\x00\x12\x12'
        return self._send_to_device(msg, 2, 3)

    def reset(self, timeout: int = 0) -> bool:
        """PC 24: remote RESET (same as pressing the RESET button).

        :param timeout: number of seconds to wait for a response, 
            defaults to 0 (and is overriden by 
            GuaritaIP.default_timeout)
        :type timeout: int, optional

        :return: *True* on success or *False* on failure.
        :rtype: bool
        """
        if timeout == 0:
            timeout = self.default_timeout
        msg = b'\x00\x18\x18'
        if self._send_to_device(msg, 3, timeout) == msg:
            return True
        else:
            return False

    def refresh_rx(self, timeout: int = 15) -> bool:
        """PC 29: Refresh receptors (send current data to them).
        
        :param timeout: number of seconds to wait for a response, 
            defaults to 15
        :type timeout: int, optional

        :return: *True* on success or *False* on failure.
        :rtype: bool
        """
        msg = b'\x00\x1d\x1d'
        if self._send_to_device(msg, 4, timeout) == b'\x00\x1d\x00\x1d':
            return True
        else:
            return False

    def read_rxfm_version(self, dev_type: int, dev_can_address: int, 
                         timeout: int = 0) -> str:
        """PC 61: Read firmware version (receptor).

        :param dev_type: integer representing the type of the receptor, 
            1 = RF
            2 = TA
            3 = CT
            5 = BM
            6 = TP
            7 = SN
        :type dev_type: int
        :param dev_can_address: the address of the receptor, from 1 to 8
        :type dev_can_address: int
        :param timeout: number of seconds to wait for a response, 
            defaults to 0 (and is overriden by 
            GuaritaIP.default_timeout)
        :type timeout: int, optional

        :return: *str* in the format <version1> + <version2> + <release> 
            + <build1> + <build2> or an empty string on failure
        :rtype: str
        """
        if timeout == 0:
            timeout = self.default_timeout
        dev_type = "0" + str(dev_type)
        dev_can_address = "0" + str(dev_can_address - 1)
        msg = self._add_checksum("003d" + dev_type + dev_can_address)
        response = self._send_to_device(msg, 11, timeout)
        if response:
            return response[4:9].decode("ascii")
        else:
            return ""




    #TODO: PC 11, PC 66, PC 92, PC 93