import re
import sys
from simple_zpl2 import ZPLDocument, Code128_Barcode, NetworkPrinter

class Label_Maker:

    INCH=2.54
    
    #what these translate to in linear cm
    DPI203 = 203
    DPI300 = 300

    def __init__(self, ipaddress, metric=False, dpi=203, width=1, height=0.5, margins=.125, columns=2):
        #note: we're defaulting to uline S-10765 dimensions
        self.height = height
        self.width = width
        self.margins = margins
        self.ipaddress = ipaddress
        self.dpi = dpi
        self.columns = columns
        self.metric=metric

    def printlabel(self, text, barcode, quantity=12):
        zpl = ZPLDocument()
        
        x_start = self.margins*self.dpi
        y_start = self.margins*self.dpi
        x_offset = self.dpi * (1/8)
        y_offset = self.dpi * (1/8)

        for c in range(self.columns):
            x_start += (self.width+self.margins)*self.dpi*c
            zpl.add_field_origin(int(x_start + x_offset), int(y_start + y_offset))
            zpl.add_field_data(text[:30]) 
            zpl.add_field_origin(int(x_start + x_offset), int(y_start + y_offset*2))
            bc = Code128_Barcode(barcode, 'N', 30, 'Y')
            zpl.add_barcode(bc)

        zpl.add_print_quantity(int(quantity/self.columns))
        
        printer = NetworkPrinter(self.ipaddress)
        printer.print_zpl(zpl)

if __name__=='__main__':
    lm = Label_Maker(ipaddress = sys.argv[1])
    lm.printlabel(sys.argv[2],sys.argv[3])