# PyARINC429

PyARINC429 provides object types used for organizing and interpreting digital information as specified by the ARINC 429 data protocol. It supports basic encoding, decoding, and validation for Binary Coded Decimal (BCD), Binary Number Representation (BNR), and discrete word types. It also supports mixed BCD/discrete and BNR/discrete data.

PyARINC429 was developed using Python 3.5.

## Example Usage

### BCD

```python
>>> word = arinc429.Word()
>>> word.label = 0o1
>>> encoded_vhf1_freq = arinc429.BCD(121.5, resolution=0.1)
>>> bit_field = arinc429.DataField(11, 29, encoded_vhf1_freq)
>>> bit_field
DataField(lsb=11, msb=29, data=BCD(value=121.5, resolution=0.1))
>>> word.set_bit_field(*bit_field)
>>> print(word)
Label=0o1, SDI=0, Data=0x1215, SSM=0, Parity=0
>>> decoded_vhf1_freq = arinc429.BCD.decode(word.data, word.ssm, 0.1)
>>> print(decoded_vhf1_freq)
121.5
```

### BNR

```python
>>> word = arinc429.Word()
>>> word.label = 0o400
ValueError: Label must be >= 0o0 and <= 0o377: 0o400
>>> word.label = 0o2
>>> encoded_pitch = arinc429.BNR(90, 0.043945313)
>>> encoded_pitch
BNR(value=89.956055711, resolution=0.043945313)
>>> bnr_bit_field = arinc429.DataField(13, 29, encoded_pitch)
>>> disc_bit_field = arinc429.DataField(11, 12, arinc429.Discrete(1))
>>> word.set_bit_field(*bnr_bit_field)
>>> print(word)
Label=0o1, SDI=0, Data=0x1ffc, SSM=0, Parity=1
>>> word.set_bit_field(*disc_bit_field)
>>> print(word)
Label=0o1, SDI=0, Data=0x1ffd, SSM=0, Parity=0
>>> arinc429.BNR.decode(word.get_bit_field(bnr_bit_field.lsb, bnr_bit_field.msb), 17, 0.043945313)
BNR(value=89.956055711, resolution=0.043945313)
```

### Discrete

```python
>>> word = arinc429.Word()
>>> word.label = 0o3
>>> encoded_mode = arinc429.Discrete(6)
>>> bit_field = arinc429.DataField(11, 12, encoded_mode)
>>> word.set_bit_field(*bit_field)
arinc429.arinc429.FieldOverflowError: 0x6 overflows 2 bit(s)
>>> bit_field = arinc429.DataField(11, 13, encoded_mode)
>>> bit_field
DataField(lsb=11, msb=13, data=Discrete(value=0x6))
>>> word.set_bit_field(*bit_field)
>>> print(word)
Label=0o3, SDI=0, Data=0x6, SSM=0, Parity=0
>>> decoded_mode = arinc429.Discrete.decode(word.data)
>>> print(decoded_mode)
6
```
