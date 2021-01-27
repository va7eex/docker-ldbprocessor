import re
import sys
from simple_zpl2 import ZPLDocument, Code128_Barcode, NetworkPrinter

class Label_Maker:

    INCH=2.54
    
    #what these translate to in linear cm
    DPI203 = 8
    DPI300 = 12

    def __init__(self, ipaddress, dpi=8, imperial=True, width=1, height=0.5, margins=.125, columns=2):
        #note: we're defaulting to uline S-10765 dimensions
        self.height = height
        self.width = width
        self.margins = margins
        self.imperial = imperial
        self.ipaddress = ipaddress
        self.dpi = dpi
        self.columns = columns

    def printlabel(self, text, barcode, quantity=12):
        zpl = ZPLDocument()
        
        x_start = self.margins*(self.imperial*self.INCH*self.dpi)
        y_start = self.margins*(self.imperial*self.INCH*self.dpi)
        x_offset = self.dpi
        y_offset = self.dpi

        for c in range(self.columns):
            x_start += (self.width+self.margins)*(self.imperial*self.INCH*self.dpi)*c
            zpl.add_field_origin(x_start + x_offset, y_start + y_offset)
            bc = Code128_Barcode(barcode, 'N', 30, 'Y')
            zpl.add_barcode(bc)

        zpl.add_print_quantity(int(quantity/self.columns))
        
        printer = NetworkPrinter(self.ipaddress)
        printer.print_zpl(zpl)

if __name__=='__main__':
    lm = Label_Maker(ipaddress = sys.argv[1])
    lm.printlabel('','test')