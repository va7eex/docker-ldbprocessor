

import sys
import re
from types import CodeType


class Barcode:

    codeTypeCS = {
        '01':'Code 39',
        '02':'Codabar',
        '03':'Code 128',
        '0C':'Code 11',
        '72':'Chinese 2 of 5',
        '04':'Discrete 2 of 5',
        '05':'IATA 2 of 5',
        '06':'Interleaved 2 of 5',
        '07':'Code 93',
        '08':'UPC-A',
        '48':'UPC-A.2',
        '88':'UPC-A.5',
        '09':'UPC-E0',
        '49':'UPC-E0.2',
        '89':'UPC-E0.5',
        '0A':'EAN-8',
        '4A':'EAN-8.2',
        '8A':'EAN-8.5',
        '0B':'EAN-13',
        '4B':'EAN-13.2',
        '8B':'EAN-13.5',
        '0E':'MSI',
        '0F':'GS1-128',
        '10':'UPC-E1',
        '50':'UPC-E1.2',
        '90':'UPC-E1.5',
        '15':'Trioptic Code 39',
        '17':'Bookland EAN',
        '23':'GS1 Databar Ltd',
        '24':'GS1 Databar Omni',
        '25':'GS1 Databar Exp'
    }

    # https://supportcommunity.zebra.com/s/article/Determine-Barcode-Symbology-by-using-Symbol-or-AIM-Code-Identifiers?language=en_US
    codeTypeAIM = {
        'A': 'Code 39',
        'C': 'Code 128',
        'd': 'Datamatrix',
        'E': 'UPC/EAN',
        'e': 'GS1 DataBar',
        'F': 'Codabar',
        'G': 'Code 93',
        'g': 'Grid Matrix',
        'H': 'Code 11',
        'h': 'Han Xin',
        'I': 'Interleaved 2 of 5',
        'L': 'PDF417',
        'L2': 'TLC 39',
        'M': 'MSI',
        'Q': 'QR Code',
        'S': 'Discrete 2 of 5',
        'U': 'Maxicode',
        'z': 'Aztec',
        'X': 'Other'
    }

    codeTypeSymbol = {
        'A': 'UPC',
        'B': 'Code 39',
        'C': 'Codabar',
        'D': 'Code 128',
        'E': 'Code 93',
        'F': 'Interleaved 2 of 5',
        'G': 'Discrete 2 of 5',
        'H': 'Code 11',
        'J': 'MSI',
        'K': 'GS1-128',
        'L': 'Bookland EAN',
        'M': 'Trioptic Code 39',
        'N': 'Coupon Code',
        'R': 'GS1 Databar',
        'S': 'Matrix 2 of 5',
        'T': 'TLC 39',
        'U': 'Chinese 2 of 5',
        'V': 'Korean 3 of 5',
        'X': 'PDF417',
        'z': 'Aztec', #is this a typo?
        'Z': 'Aztec', #just in case this is a typo.
        'P00': 'Data Matrix',
        'P01': 'QR Code',
        'P02': 'Maxicode',
        'P03': 'US Postnet',
        'P04': 'US Planet',
        'P05': 'Japan Postal',
        'P06': 'UK Postal',
        'P08': 'Netherlands KIX Code',
        'P09': 'Australia Post',
        'P0A': 'USPS 4CB/Intelligent Mail',
        'P0B': 'UPU FICS Postal',
        'P0C': 'Mailmark',
        'P0D': 'Grid Matrix',
        'P0G': 'GS1 Datamatrix',
        'P0H': 'Han Xin',
        'P0Q': 'GS1 QR',
        'P0X': 'Signature Capture'
    }

    def __init__(self):
        pass

    def BarcodeType(barcode: str, prefix: str = "", suffix: str = ""):
        """
        Implementation of detecting barcodes based on this:
        """
        if ',' in barcode:
            prefix, barcode = barcode.split(',',maxsplit=2)
            if ',' in barcode:
                barcode, suffix = barcode.split(',',maxsplit=2)

        aim = re.compile('^\][a-zA-Z]')     # technically this should conform to ]Cm,
                                            # but since the m field is used once for a symbology
                                            # I don't care about we'll ignore it
        cs = re.compile('^\w{2}')
        symbol = re.compile('^[A-Z]|P0\w')

        if 'aim' in prefix:
            m = aim.match(barcode)
            if m is not None:
                return barcode.replace(m.group(),''), Barcode.codeTypeAIM.get(m.group()[1:], None)
        elif 'cs' in prefix:
            m = cs.match(barcode)
            if m is not None:
                return barcode.replace(m.group(),''), Barcode.codeTypeCS.get(m.group(), None)
        elif 'symbol' in prefix:
            m = symbol.match(barcode)
            if m is not None:
                return barcode.replace(m.group(),''), Barcode.codeTypeSymbol.get(m.group(), None)
        else:
            # AIM is pretty easy to detect, so we'll make it the catch-all
            if ']' in barcode[0]:
                m = aim.match(barcode)
                if m is not None:
                    return barcode.replace(m.group(),''), Barcode.codeTypeAIM.get(m.group()[1:], None)

        return barcode, None

    def __oddeven(barcode):
        """Split each digit into even and odd groups from the RIGHTMOST POSITION"""
        odd = []
        even = []
        barcode = barcode[::-1] # even and odd numbers are based from the rightmost position.
        for c in range(len(barcode)):
            #even/odd is reversed because we start at position 0, not position 1
            if c%2 == 1:
                even.append(int(barcode[c]))
            else:
                odd.append(int(barcode[c]))

        return odd, even

    def __mod10(barcode):
        """
        Mod 10:
        FROM RIGHT TO LEFT
        1. Add up all the odd numbers in the code, multiply the sum by 3.
        2. Add up all even numbers.
        3. 10-((even sum)+(odd sum) % 10) = check digit
        4. check digit % 10 again just for edge cases were the check digit is 10
        """
        odd, even = Barcode.__oddeven(barcode)
        print(even,odd,sum(even),sum(odd))

        mod10 = (10-((sum(even)+sum(odd)*3)%10)) %10
        print(f'Mod10: {mod10}')
        return mod10

    def GTIN14(barcode: str):
        """Determine whether a GTIN-14 is a valid code."""
        return Barcode.Interleaved2of5(barcode)

    def Interleaved2of5(barcode: str):
        """Determine whether an Interleaved 2 of 5 passes its check digit."""

        if type(barcode) is not str:
            barcode = f"{barcode}"

        if type(barcode) is str and not barcode.isdigit():
            raise False
        
        return int(barcode[-1:]) == Barcode.__mod10(barcode[:-1])

    def CalculateUPC(itf14: str):
        """Calculate GTIN-12 aka UPC code based on GTIN-14"""
        if type(itf14) is not str:
            itf14 = f'{itf14}'
        if not itf14.isdigit():
            return 0
            
        gtin12 = f'{itf14[-12:-1]}{Barcode.__mod10(itf14[-12:-1])}'

        return gtin12

    def CalculateEAN(itf14: str):
        """Calculate GTIN-13 aka EAN code based on GTIN-14"""
        if type(itf14) is not str:
            itf14 = f'{itf14}'
        if not itf14.isdigit():
            return 0
            
        gtin13 = f'{itf14[-13:-1]}{Barcode.__mod10(itf14[-13:-1])}'

        return gtin13


if __name__ == "__main__":
    print('Passes GTIN-14 check:', Barcode.Interleaved2of5(sys.argv[1]))
    print('Calculated UPC-A:', Barcode.CalculateUPC(sys.argv[1]))
    print('Calculated EAN-13:', Barcode.CalculateEAN(sys.argv[1]))