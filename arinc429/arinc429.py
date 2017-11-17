"""
Provides classes and data used for organizing and interpreting ARINC 429
data.
"""

from abc import ABCMeta, abstractmethod
from decimal import Decimal
from typing import NamedTuple, Union


class BitFieldRange(NamedTuple):
    """A named and typed tuple for specifying the range of a bit field."""

    lsb: int
    msb: int


# Least significant bit. The indexing of ARINC 429 bits is 1-based.
LSB = 1
# Most significant bit
MSB = 32
# Label bits
LABEL_BITS = BitFieldRange(1, 8)
# Source/Destination Identifier (SDI) bits
SDI_BITS = BitFieldRange(9, 10)
# Data bits
DATA_BITS = BitFieldRange(11, 29)
# Sign/Status Matrix (SSM) bits
SSM_BITS = BitFieldRange(30, 31)
# Parity bit
PARITY_BIT = MSB
# Mapping of labels to bit-reversed labels.
LABELS = {label: int(format(label, "08b")[::-1], 2)
          for label in range(0o0, 0o400)}


class ARINC429Error(Exception):
    """Base class for ARINC 429 exceptions."""


class FieldOverflowError(ARINC429Error):
    """
    Exception that occurs when attempting to assign a value to a bit field of
    insufficient length.
    """

    def __init__(self, value: int, bit_length: int) -> None:
        super().__init__("{:#x} overflows {} bit(s)".format(value, bit_length))


class DataFieldType(metaclass=ABCMeta):
    """
    Base class for ARINC 429 data types.

    Defines numeric operations that integrate subclass instances with Word
    instances.
    """

    def __init__(self, value: int = 0) -> None:
        """
        Form a datum based on value.

        value is the initial value of the DataFieldType instance.
        """
        # Initialize the value of the datum.
        self._value = int(value)

    def __eq__(self, other) -> bool:
        return (isinstance(other, self.__class__) and
                self.__dict__ == other.__dict__)

    # The __lt__, __gt__, and __and__ methods emulate numeric operations
    # that are used by the Word.set_bit_field method.

    def __lt__(self, other) -> bool:
        return (self._value < other
                if isinstance(other, int)
                else NotImplemented)

    def __le__(self, other) -> bool:
        return (self._value <= other
                if isinstance(other, int)
                else NotImplemented)

    def __gt__(self, other) -> bool:
        return (self._value > other
                if isinstance(other, int)
                else NotImplemented)

    def __ge__(self, other) -> bool:
        return (self._value >= other
                if isinstance(other, int)
                else NotImplemented)

    def __and__(self, other) -> bool:
        return (self._value & other
                if isinstance(other, int)
                else NotImplemented)

    def __int__(self) -> int:
        return self._value

    def __format__(self, format_spec: str) -> str:
        return self._value.__format__(format_spec)

    @classmethod
    @abstractmethod
    def decode(cls, **kwargs) -> "DataFieldType":
        _ = kwargs
        return DataFieldType()


class DataField(NamedTuple):
    """
    A typed, named tuple for specifying data fields.

    This kind of tuple can be unpacked to provide arguments for the
    Word.set_bit_field method.
    """

    lsb: int
    msb: int
    data: Union[int, DataFieldType]


# Type alias for data field values.
DataFieldValue = Union[int, float, Decimal]


class BCD(DataFieldType):
    """Interprets binary coded decimal (BCD) values."""

    # Sign/Status Matrix
    PLUS = NORTH = EAST = RIGHT = TO = ABOVE = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    MINUS = SOUTH = WEST = LEFT = FROM = BELOW = 3

    def __init__(self,
                 value: DataFieldValue = 0,
                 resolution: DataFieldValue = 1) -> None:
        """
        Form a BCD datum based on value.

        value is the initial value of the BCD instance.

        resolution is the scale of each BCD digit.
        """
        # Calculate the significant digits.
        value = Decimal(str(value))
        resolution = Decimal(str(resolution))
        # Calculate the value as a multiple of the resolution.
        encoded_value = value // resolution
        # Decompose the value.
        minus, digits, _ = encoded_value.as_tuple()
        # Retain the decoded value.
        self._decoded_value = encoded_value * resolution
        # Retain the resolution.
        self._resolution = resolution
        # Determine the sign of the value.
        self._sign = self.MINUS if minus else self.PLUS
        # Convert the value to BCD.
        bcd_value = 0
        for digit in digits:
            bcd_value = (bcd_value << 4) | digit
        super().__init__(bcd_value)

    def __int__(self) -> int:
        return int(self._decoded_value)

    def __float__(self) -> float:
        return float(self._decoded_value)

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}(value={self._decoded_value!s}, "
                "resolution={self.resolution})").format(self=self)

    def __str__(self) -> str:
        return str(self._decoded_value)

    @property
    def resolution(self) -> Decimal:
        """Return the resolution of significant digits."""
        return self._resolution

    @property
    def sign(self) -> int:
        """Return the sign code of the BCD datum."""
        return self._sign

    @classmethod
    def decode(cls,
               bcd_value: int,
               bcd_sign: int,
               resolution: DataFieldValue = 1) -> "BCD":
        """
        Return an instance of BCD based on encoded data.

        bcd_value is a binary-coded decimal (BCD) encoded number.

        bcd_sign is the sign/status matrix (SSM) code representing the sign of
        the decoded value.

        resolution is the scale of each BCD digit.
        """
        # Compute the sign.
        sign = -1 if bcd_sign == cls.MINUS else 1
        # Decode the BCD value.
        int_value = int(format(bcd_value, "x"), 10)
        value = sign * Decimal(int_value) * Decimal(str(resolution))
        # Return a BCD instance.
        return cls(value, resolution)


class BNR(DataFieldType):
    """Interprets binary number representation (BNR) values."""

    # Sign Matrix
    PLUS = NORTH = EAST = RIGHT = TO = ABOVE = 0
    MINUS = SOUTH = WEST = LEFT = FROM = BELOW = 1
    # Status Matrix
    FAILURE_WARNING = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    NORMAL_OPERATION = 3

    def __init__(self,
                 value: DataFieldValue = 0,
                 resolution: DataFieldValue = 1) -> None:
        """
        Form a BNR datum based on value. The BNR value will be adjusted to the
        lesser multiple of resolution in the case that value is not already a
        multiple of resolution.

        value is the initial value of the BNR instance.

        resolution is the scaling factor used when applying binary scaling to
        the BNR instance.
        """
        # Convert the value to BNR.
        value = Decimal(str(value))
        resolution = Decimal(str(resolution))
        bnr_value = value // resolution
        super().__init__(bnr_value)
        # Adjust the value to a multiple of the bit scale, and retain the
        # result as the decoded value.
        self._decoded_value = bnr_value * resolution
        # Retain the resolution.
        self._resolution = resolution

    def __int__(self) -> int:
        return int(self._decoded_value)

    def __float__(self) -> float:
        return float(self._decoded_value)

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}(value={self._decoded_value}, "
                "resolution={self.resolution})").format(self=self)

    def __str__(self) -> str:
        return str(self._decoded_value)

    @property
    def resolution(self) -> Decimal:
        """Return the scaling factor."""
        return self._resolution

    @classmethod
    def decode(cls,
               bnr_value: int,
               bnr_bit_length: int,
               resolution: DataFieldValue = 1) -> "BNR":
        """
        Return an instance of BNR based on encoded data.

        bnr_value is encoded data in the signed, two's complement binary number
        form.

        bnr_bit_length is the number of bits that represent bnr_value.

        resolution is the scaling factor used when applying binary scaling to
        bnr_value.
        """
        # Extract the value of the sign bit.
        sign = (bnr_value >> (bnr_bit_length - 1)) & 1
        # Set the sign of the Python number. This performs sign extension when
        # the sign is negative.
        bnr_value -= sign << bnr_bit_length
        # Decode the BNR value.
        value = bnr_value * resolution
        # Return a BNR instance.
        return cls(value, resolution)


class Discrete(DataFieldType):
    """Interprets discrete values."""

    # Status Matrix
    NORMAL_OPERATION = VERIFIED_DATA = 0
    NO_COMPUTED_DATA = 1
    FUNCTIONAL_TEST = 2
    FAILURE_WARNING = 3

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}"
                "(value={self._value:#x})").format(self=self)

    def __str__(self) -> str:
        return str(self._value)

    @classmethod
    def decode(cls, discrete_value: int) -> "Discrete":
        """
        Return an instance of Discrete based on encoded data.

        discrete_value is the integer value of a field of discrete bits.
        """
        # Return a Discrete instance.
        return cls(discrete_value)


class Word(object):
    """Interprets and validates the composition of a word."""

    EVEN_PARITY = 0
    ODD_PARITY = 1

    def __init__(self, value: int = 0, parity_type: int = ODD_PARITY) -> None:
        """Form a basic ARINC 429 word based on value and parity_type."""
        self._value = 0
        self._parity_type = 0
        # Initialize the word.
        self.parity_type = parity_type
        self.set_bit_field(LSB, MSB, value)

    def __int__(self) -> int:
        return self._value

    def __index__(self) -> int:
        return self._value

    def __repr__(self) -> str:
        return ("{self.__class__.__qualname__}"
                "({self._value:#x})").format(self=self)

    def __str__(self) -> str:
        return ("Label={self.label:#o}, SDI={self.sdi}, Data={self.data:#x}, "
                "SSM={self.ssm}, Parity={self.parity}".format(self=self))

    def __format__(self, format_spec: str) -> str:
        return self._value.__format__(format_spec)

    @property
    def label(self) -> int:
        """Return the current label value."""
        # Extract the label, and return its bit-reversed counterpart.
        return LABELS[self.get_bit_field(*LABEL_BITS)]

    @label.setter
    def label(self, value: int) -> None:
        """
        Change the label value.

        value should be within the range 0o0-0o377 inclusive. ValueError is
        raised if value is out of range.
        """
        try:
            # Apply the bit-reversed label.
            self.set_bit_field(*LABEL_BITS, LABELS[value])
        except KeyError:
            raise ValueError("Label must be >= {:#o} and <= {:#o}: "
                             "{:#o}".format(min(LABELS), max(LABELS), value))

    @property
    def sdi(self) -> int:
        """Return the current SDI setting."""
        return self.get_bit_field(*SDI_BITS)

    @sdi.setter
    def sdi(self, value: int) -> None:
        """Change the SDI setting."""
        self.set_bit_field(*SDI_BITS, value)

    @property
    def data(self) -> int:
        """Return the current value in the data field."""
        return self.get_bit_field(*DATA_BITS)

    @data.setter
    def data(self, value: int) -> None:
        """Change the value in the data field."""
        self.set_bit_field(*DATA_BITS, value)

    @property
    def ssm(self) -> int:
        """Return the current SSM setting."""
        return self.get_bit_field(*SSM_BITS)

    @ssm.setter
    def ssm(self, value: int) -> None:
        """Change the SSM setting."""
        self.set_bit_field(*SSM_BITS, value)

    @property
    def parity(self) -> int:
        """Return the current parity bit setting."""
        return self.get_bit_field(PARITY_BIT, PARITY_BIT)

    @property
    def parity_type(self) -> int:
        """Return the current parity setting."""
        return self._parity_type

    @parity_type.setter
    def parity_type(self, value: int) -> None:
        """Change the parity setting."""
        if value in (self.EVEN_PARITY, self.ODD_PARITY):
            self._parity_type = value
            # Refresh the parity bit.
            self.set_bit_field(LSB, MSB, self._value)
        else:
            raise ValueError("Parity setting must be {cls.EVEN_PARITY} or "
                             "{cls.ODD_PARITY}: {0}".format(value, cls=self))

    @staticmethod
    def _validate_bit_field_range(lsb: int, msb: int) -> None:
        if lsb < LSB:
            raise ValueError("LSB must be >= {} and <= {}: "
                             "{}".format(LSB, MSB, lsb))
        elif msb > MSB:
            raise ValueError("MSB must be >= {} and <= {}: "
                             "{}".format(LSB, MSB, msb))
        elif msb < lsb:
            raise ValueError("MSB must be >= LSB: {}".format(msb))

    @staticmethod
    def _validate_bit_length(bit_length: int, value: int) -> None:
        if bit_length > 0:
            # Compute the maximum value that can be represented by bit_length
            # bits.
            max_value = (1 << bit_length) - 1
            # Compute the minimum value that can be represented by bit_length
            # bits. Note that negative numbers in Python "are represented in a
            # variant of 2’s complement which gives the illusion of an infinite
            # string of sign bits extending to the left" (See the Data Model of
            # The Python Language Reference).
            min_value = ~(max_value >> 1)
            # Verify that the number of significant bits of the value is not
            # greater than the bit length of the value.
            if not (min_value <= value <= max_value):
                raise FieldOverflowError(value, bit_length)
        else:
            raise ValueError("Bit length must be > 0")

    def get_bit_field(self, lsb: int, msb: int) -> int:
        """
        Return the value of a bit field.

        lsb is the least significant bit (LSB) of a bit field, and is relative
        to the LSB of the containing ARINC 429 word.

        msb is the most significant bit (MSB) of a bit field, and is relative
        to the LSB of the containing ARINC 429 word.
        """
        # Validate the range of the bit field.
        self._validate_bit_field_range(lsb, msb)
        # Calculate the length of the bit field.
        bit_field_length = msb - lsb + 1
        # Calculate the offset relative to the LSB of the word.
        bit_field_offset = lsb - 1
        # Compute the bit mask.
        word_mask = (1 << bit_field_length) - 1
        # Extract the value of the bit field from the word.
        bit_field_value = (self._value >> bit_field_offset) & word_mask
        # Return the value of the bit field.
        return bit_field_value

    def set_bit_field(self,
                      lsb: int,
                      msb: int,
                      value: Union[int, DataFieldType]) -> None:
        """
        Change the value of a bit field.

        lsb is the least significant bit (LSB) of a bit field, and is relative
        to the LSB of the containing ARINC 429 word.

        msb is the most significant bit (MSB) of a bit field, and is relative
        to the LSB of the containing ARINC 429 word.

        value is applied to the bit field specified by lsb and msb.
        """
        # Validate the range of the bit field.
        self._validate_bit_field_range(lsb, msb)
        # Calculate the length of the bit field.
        bit_field_length = msb - lsb + 1
        # Validate the length of the bit field.
        self._validate_bit_length(bit_field_length, value)
        # Calculate the offsets relative to the LSB of the word.
        bit_field_offset = lsb - 1
        parity_bit_offset = PARITY_BIT - 1
        # Compute the bit masks.
        value_mask = (1 << bit_field_length) - 1
        parity_mask = (1 << parity_bit_offset) - 1
        word_mask = ~(value_mask << bit_field_offset)
        # Mask off any sign bits that extend beyond the MSB of the bit field,
        # and then shift the value into alignment with the bit field.
        bit_field_value = (value & value_mask) << bit_field_offset
        # Update the bit field.
        self._value = (self._value & word_mask) | bit_field_value
        # Count the number of 1-bits in the ARINC 429 word, excluding the
        # parity bit.
        count = format(self, "032b").count("1", 1)
        # Compute the parity bit value respective of the parity setting.
        parity_value = ((count + self._parity_type) % 2) << parity_bit_offset
        # Update the parity bit.
        self._value = (self._value & parity_mask) | parity_value
