# MSX Red Book - PSG (AY-3-8910) - Programmable Sound Generator

Original chapter: `chapter_3`

---

<a name="chapter_3"></a>
# 3. Programmable Sound Generator

As well as controlling three sound channels the 8910 PSG contains two eight bit data ports, called A and B, through which it interfaces the joysticks and the cassette input. The PSG appears to the Z80 as three I/O ports called the [Address Port](#address_port), the [Data Write Port](#data_write_port) and the [Data Read Port](#data_read_port).

<a name="address_port"></a>
## Address Port (I/O port A0H)

The PSG contains sixteen internal registers which completely define its operation. A specific register is selected by writing its number, from 0 to 15, to this port. Once selected, repeated accesses to that register may be made via the two data ports.

<a name="data_write_port"></a>
## Data Write Port (I/O port A1H)

This port is used to write to any register once it has been selected by the [Address Port](#address_port).

<a name="data_read_port"></a>
## Data Read Port (I/O port A2H)

This port is used to read any register once it has been selected by the [Address Port](#address_port).

<a name="registers_0_and_1"></a>
## Registers 0 and 1

<a name="figure25"></a>![][CH03F25]

**Figure 25**

These two registers are used to define the frequency of the Tone Generator for Channel A. Variable frequencies are produced by dividing a fixed master frequency with the number held in Registers 0 and 1, this number can be in the range 1 to 4095. Register 0 holds the least significant eight bits and Register 1 the most significant four. The PSG divides an external 1.7897725 MHz frequency by sixteen to produce a Tone Generator master frequency of 111,861 Hz. The output of the Tone Generator can therefore range from 111,861 Hz (divide by 1) down to 27.3 Hz (divide by 4095). As an example to produce a middle "`A`" (440 Hz) the divider value in Registers 0 and 1 would be 254.

<a name="registers_2_and_3"></a>
## Registers 2 and 3

These two registers control the Channel B Tone Generator as for Channel A.

<a name="registers_4_and_5"></a>
## Registers 4 and 5

These two registers control the Channel C Tone Generator as for Channel A.

<a name="register_6"></a>
## Register 6

<a name="figure26"></a>![][CH03F26]

**Figure 26**

In addition to three square wave Tone Generators the PSG contains a single Noise Generator. The fundamental frequency of the noise source can be controlled in a similar fashion to the Tone Generators. The five least significant bits of Register 6 hold a divider value from 1 to 31. The Noise Generator master frequency is 111,861 Hz as before.

<a name="register_7"></a>
## Register 7

<a name="figure27"></a>![][CH03F27]

**Figure 27**

This register enables or disables the Tone Generator and Noise Generator for each of the three channels: 0=Enable 1=Disable. It also controls the direction of interface ports A and B, to which the joysticks and cassette are attached: 0=Input, 1=Output. Register 7 must always contain 10xxxxxx or possible damage could result to the PSG, there are active devices connected to its I/O pins. The BASIC "`SOUND`" statement will force these bits to the correct value for Register 7 but there is no protection at the machine code level.

<a name="register_8"></a>
## Register 8

<a name="figure28"></a>![][CH03F28]

**Figure 28**

The four Amplitude bits determine the amplitude of Channel A from a minimum of 0 to a maximum of 15. The Mode bit selects either fixed or modulated amplitude: 0=Fixed, 1=Modulated. When modulated amplitude is selected the fixed amplitude value is ignored and the channel is modulated by the output from the Envelope Generator.

<a name="register_9"></a>
## Register 9

This register controls the amplitude of Channel B as for Channel A.

<a name="register_10"></a>
## Register 10

This register controls the amplitude of Channel C as for Channel A.

<a name="registers_11_and_12"></a>
## Registers 11 and 12

<a name="figure29"></a>![][CH03F29]

**Figure 29**

These two registers control the frequency of the single Envelope Generator used for amplitude modulation. As for the Tone Generators this frequency is determined by placing a divider count in the registers. The divider value may range from 1 to 65535 with Register 11 holding the least significant eight bits and Register 12 the most significant. The master frequency for the Envelope Generator is 6991 Hz so the envelope frequency may range from 6991 Hz (divide by 1) to 0.11 Hz (divide by 65535).

<a name="register_13"></a>
## Register 13

<a name="figure30"></a>![][CH03F30]

**Figure 30**

The four Envelope Shape bits determine the shape of the amplitude modulation envelope produced by the Envelope Generator:

<a name="figure31"></a>![][CH03F31]

**Figure 31**

<a name="register_14"></a>
## Register 14

<a name="figure32"></a>![][CH03F32]

**Figure 32**

This register is used to read in PSG Port A. The six joystick bits reflect the state of the four direction switches and two trigger buttons on a joystick: 0=Pressed, 1=Not pressed. Alternatively up to six Paddles may be connected instead of one joystick. Although most MSX machines have two 9 pin joystick connectors only one can be read at a time. The one to be selected for reading is determined by the Joystick Select bit in [PSG Register 15](#register_15).

The Keyboard Mode bit is unused on UK machines. On Japanese machines it is tied to a jumper link to determine the keyboard's character set.

The Cassette Input is used to read the signal from the cassette EAR output. This is passed through a comparator to clean the edges and to convert to digital levels but is otherwise unprocessed.

<a name="register_15"></a>
## Register 15

<a name="figure33"></a>![][CH03F33]

**Figure 33**

This register is used to output to PSG Port B. The four least significant bits are connected via TTL open-collector buffers to pins 6 and 7 of each joystick connector. They are normally set to a 1, when a paddle or joystick is connected, so that the pins can function as inputs. When a touchpad is connected they are used as handshaking outputs.

The two Pulse bits are used to generate a short positive- going pulse to any paddles attached to joystick connectors 1 or 2. Each paddle contains a monostable timer with a variable resistor controlling its pulse length. Once the timer is triggered the position of the variable resistor can be determined by counting until the monostable times out.

The Joystick Select bit determines which joystick connector is connected to PSG Port A for input: 0=Connector 1, 1=Connector 2.

The Kana LED output is unused on UK machines. On Japanese machines it is used to drive a keyboard mode indicator.

<br><br><br>
