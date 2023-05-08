EESchema Schematic File Version 4
EELAYER 30 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title ""
Date ""
Rev ""
Comp ""
Comment1 ""
Comment2 ""
Comment3 ""
Comment4 ""
$EndDescr
$Comp
L power:+3.3V #PWR0103
U 1 1 63973190
P 3950 1700
F 0 "#PWR0103" H 3950 1550 50  0001 C CNN
F 1 "+3.3V" V 3965 1828 50  0000 L CNN
F 2 "" H 3950 1700 50  0001 C CNN
F 3 "" H 3950 1700 50  0001 C CNN
	1    3950 1700
	0    -1   -1   0   
$EndComp
$Comp
L power:+3.3V #PWR0104
U 1 1 63973196
P 4450 1700
F 0 "#PWR0104" H 4450 1550 50  0001 C CNN
F 1 "+3.3V" V 4465 1828 50  0000 L CNN
F 2 "" H 4450 1700 50  0001 C CNN
F 3 "" H 4450 1700 50  0001 C CNN
	1    4450 1700
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0105
U 1 1 6397319C
P 3950 1600
F 0 "#PWR0105" H 3950 1350 50  0001 C CNN
F 1 "GND" V 3950 1450 50  0000 R CNN
F 2 "" H 3950 1600 50  0001 C CNN
F 3 "" H 3950 1600 50  0001 C CNN
	1    3950 1600
	0    1    1    0   
$EndComp
$Comp
L power:GND #PWR0106
U 1 1 639731A2
P 4450 1600
F 0 "#PWR0106" H 4450 1350 50  0001 C CNN
F 1 "GND" V 4455 1472 50  0000 R CNN
F 2 "" H 4450 1600 50  0001 C CNN
F 3 "" H 4450 1600 50  0001 C CNN
	1    4450 1600
	0    -1   -1   0   
$EndComp
Text GLabel 3950 1200 0    50   Input ~ 0
FLASH_SIO0_SI
Text GLabel 3950 1300 0    50   Input ~ 0
FLASH_SCLK
Text GLabel 4450 1400 2    50   Input ~ 0
FLASH_CSn
Text GLabel 4450 1200 2    50   Input ~ 0
FLASH_SIO2_WP
Text GLabel 3950 1400 0    50   Input ~ 0
FLASH_SIO3_HOLD
Text GLabel 4450 1300 2    50   Input ~ 0
FLASH_SIO1_SO
Text Notes 3100 1550 0    50   ~ 0
PMOD-6
Text Notes 5000 1550 0    50   ~ 0
PMOD-5
Text Notes 3100 1250 0    50   ~ 0
PMOD-12
Text Notes 5000 1250 0    50   ~ 0
PMOD-11
$Comp
L Connector_Generic:Conn_02x06_Odd_Even J1
U 1 1 639731B4
P 4250 1500
F 0 "J1" H 4300 975 50  0000 C CNN
F 1 "Conn_02x06_Odd_Even" H 4300 1066 50  0000 C CNN
F 2 "Connector_PinSocket_2.54mm:PinSocket_2x06_P2.54mm_Horizontal" H 4250 1500 50  0001 C CNN
F 3 "~" H 4250 1500 50  0001 C CNN
	1    4250 1500
	-1   0    0    1   
$EndComp
$Comp
L power:+3.3V #PWR0102
U 1 1 63975D50
P 7200 1700
F 0 "#PWR0102" H 7200 1550 50  0001 C CNN
F 1 "+3.3V" V 7215 1828 50  0000 L CNN
F 2 "" H 7200 1700 50  0001 C CNN
F 3 "" H 7200 1700 50  0001 C CNN
	1    7200 1700
	0    1    1    0   
$EndComp
Text GLabel 7200 1600 2    50   Input ~ 0
FLASH_SIO0_SI
Text GLabel 7200 1400 2    50   Input ~ 0
FLASH_SCLK
Text GLabel 6700 1400 0    50   Input ~ 0
FLASH_CSn
Text GLabel 5875 2150 0    50   Input ~ 0
FLASH_SIO2_WP
Text GLabel 5875 2250 0    50   Input ~ 0
FLASH_SIO3_HOLD
Text GLabel 7200 1500 2    50   Input ~ 0
FLASH_SIO1_SO
$Comp
L Connector_Generic:Conn_02x06_Odd_Even J2
U 1 1 63975D6C
P 7000 1500
F 0 "J2" H 7050 975 50  0000 C CNN
F 1 "Conn_02x06_Odd_Even" H 7050 1066 50  0000 C CNN
F 2 "Connector_PinSocket_2.54mm:PinSocket_2x06_P2.54mm_Horizontal" H 7000 1500 50  0001 C CNN
F 3 "~" H 7000 1500 50  0001 C CNN
	1    7000 1500
	-1   0    0    1   
$EndComp
Text Notes 7275 1225 0    50   ~ 0
PI-27
Text Notes 6425 1225 0    50   ~ 0
PI-28
Text Notes 6400 1725 0    50   ~ 0
PI-18
Text Notes 7275 1725 0    50   ~ 0
PI-17
$Comp
L power:GND #PWR0108
U 1 1 63975D5C
P 7200 1300
F 0 "#PWR0108" H 7200 1050 50  0001 C CNN
F 1 "GND" V 7205 1172 50  0000 R CNN
F 2 "" H 7200 1300 50  0001 C CNN
F 3 "" H 7200 1300 50  0001 C CNN
	1    7200 1300
	0    -1   -1   0   
$EndComp
$Comp
L power:GND #PWR0107
U 1 1 63975D56
P 6700 1600
F 0 "#PWR0107" H 6700 1350 50  0001 C CNN
F 1 "GND" V 6700 1450 50  0000 R CNN
F 2 "" H 6700 1600 50  0001 C CNN
F 3 "" H 6700 1600 50  0001 C CNN
	1    6700 1600
	0    1    1    0   
$EndComp
NoConn ~ 6700 1500
NoConn ~ 6700 1300
NoConn ~ 3950 1500
NoConn ~ 4450 1500
NoConn ~ 6700 1200
NoConn ~ 7200 1200
NoConn ~ 5875 2250
NoConn ~ 5875 2150
Text Notes 6000 2225 0    50   ~ 0
pulled-up on pmod
Text Notes 4950 1425 0    50   ~ 0
pulled-up on pmod
$EndSCHEMATC
