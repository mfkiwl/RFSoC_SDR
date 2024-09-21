from backend import *
from backend import be_np as np, be_scp as scipy
from general import General




class Tcp_Comm(General):
    def __init__(self, params):
        super().__init__(params)

        self.mode = params.mode
        self.fc = params.fc
        self.beam_test = params.beam_test
        self.server_ip = params.server_ip
        self.TCP_port_Cmd = params.TCP_port_Cmd
        self.TCP_port_Data = params.TCP_port_Data
        self.tcp_localIP = params.tcp_localIP
        self.tcp_bufferSize = params.tcp_bufferSize
        self.adc_bits = params.adc_bits
        self.dac_bits = params.dac_bits
        self.RFFE = params.RFFE
        self.n_frame_rd = params.n_frame_rd
        self.n_samples = params.n_samples
        self.n_tx_ant = params.n_tx_ant
        self.n_rx_ant = params.n_rx_ant

        if self.RFFE=='sivers':
            self.tx_bb_gain = 0x3
            self.tx_bb_phase = 0x0
            self.tx_bb_iq_gain = 0x77
            self.tx_bfrf_gain = 0x7F
            self.rx_gain_ctrl_bb1 = 0x33
            self.rx_gain_ctrl_bb2 = 0x00
            self.rx_gain_ctrl_bb3 = 0x33
            self.rx_gain_ctrl_bfrf = 0x7F

        self.nbytes = 2
        self.nread = self.n_rx_ant * self.n_frame_rd * self.n_samples

        self.print("Client object init done, Succesfully connected to the server", thr=1)


    def close(self):
        self.radio_control.close()
        self.radio_data.close()
        self.print("Client object closed", thr=1)

    def __del__(self):
        self.close()
        self.print("Client object deleted", thr=1)

    def init_tcp_server(self):
        ## TCP Server
        self.print("Starting TCP server", thr=1)
        
        ## Command
        self.TCPServerSocketCmd = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)# Create a datagram socket
        self.TCPServerSocketCmd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.TCPServerSocketCmd.bind((self.tcp_localIP, self.TCP_port_Cmd)) # Bind to address and ip
        
        ## Data
        self.TCPServerSocketData = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)         # Create a datagram socket
        self.TCPServerSocketData.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.TCPServerSocketData.bind((self.tcp_localIP, self.TCP_port_Data))                # Bind to address and ip

        bufsize = self.TCPServerSocketData.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF) 
        # self.print ("Buffer size [Before]:%d" %bufsize, thr=2)
        self.print("TCP server is up", thr=1)
        
    def init_tcp_client(self):
        self.radio_control = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.radio_control.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.radio_control.connect((self.server_ip, self.TCP_port_Cmd))

        self.radio_data = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        self.radio_data.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.radio_data.connect((self.server_ip, self.TCP_port_Data))

    def set_mode(self, mode):
        if mode == 'RXen0_TXen1' or mode == 'RXen1_TXen0' or mode == 'RXen0_TXen0':
            self.radio_control.sendall(b"setModeSiver "+str.encode(str(mode)))
            data = self.radio_control.recv(1024)
            self.print("Result of set_mode: {}".format(data),thr=1)
            return data
        
    def set_frequency(self, fc):
        self.radio_control.sendall(b"setCarrierFrequency "+str.encode(str(fc)))
        data = self.radio_control.recv(1024)
        self.print("Result of set_frequency: {}".format(data),thr=1)
        return data

    def set_tx_gain(self):
        self.radio_control.sendall(b"setGainTX " + str.encode(str(int(self.tx_bb_gain)) + " ") \
                                                    + str.encode(str(int(self.tx_bb_phase)) + " ") \
                                                    + str.encode(str(int(self.tx_bb_iq_gain)) + " ") \
                                                    + str.encode(str(int(self.tx_bfrf_gain))))
        data = self.radio_control.recv(1024)
        self.print("Result of set_tx_gain: {}".format(data),thr=1)
        return data

    def set_rx_gain(self):
        self.radio_control.sendall(b"setGainRX " + str.encode(str(int(self.rx_gain_ctrl_bb1)) + " ") \
                                                    + str.encode(str(int(self.rx_gain_ctrl_bb2)) + " ") \
                                                    + str.encode(str(int(self.rx_gain_ctrl_bb3)) + " ") \
                                                    + str.encode(str(int(self.rx_gain_ctrl_bfrf))))
        data = self.radio_control.recv(1024)
        self.print("Result of set_rx_gain: {}".format(data),thr=1)
        return data

    def transmit_data(self):
        self.radio_control.sendall(b"transmitSamples")
        data = self.radio_control.recv(1024)
        self.print("Result of transmit_data: {}".format(data),thr=1)
        return data

    def receive_data(self, mode='once'):
        if mode=='once':
            nbeams = 1
            self.radio_control.sendall(b"receiveSamplesOnce")
        elif mode=='beams':
            nbeams = len(self.beam_test)
            self.radio_control.sendall(b"receiveSamples")
        nbytes = nbeams * self.nbytes * self.nread * 2
        buf = bytearray()

        while len(buf) < nbytes:
            data = self.radio_data.recv(nbytes)
            buf.extend(data)
        data = np.frombuffer(buf, dtype=np.int16)
        data = data/(2 ** (self.adc_bits + 1) - 1)
        rxtd = data[:self.nread*nbeams] + 1j*data[self.nread*nbeams:]
        rxtd = rxtd.reshape(nbeams, self.n_rx_ant, self.nread//self.n_rx_ant)
        return rxtd
    
