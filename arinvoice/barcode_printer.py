import re
import sys
from simple_zpl2 import ZPLDocument, Code128_Barcode, NetworkPrinter

class Label_Maker:

    INCH=2.54
    
    #what these translate to in linear cm
    DPI203 = 203
    DPI300 = 300

    def __init__(self, ipaddress, metric=False, dpi=203, width=1, height=0.5, margins=(1/16), columns=2, fontsize=30):
        #note: we're defaulting to uline S-10765 dimensions
        self.height = height
        self.width = width
        self.margins = margins
        self.ipaddress = ipaddress
        self.dpi = dpi
        self.columns = columns
        self.metric=metric
        self.fontsize=fontsize

    def printlabel(self, text, barcode, quantity=12):
        zpl = ZPLDocument()
        
        x_start = self.margins*self.dpi
        y_start = self.margins*2*self.dpi
        x_offset = self.dpi * (1/16)
        y_offset = self.dpi * (1/16)

        zpl.add_default_font('0', character_height=self.fontsize)

        for c in range(self.columns):
            x_start += (self.width+self.margins)*self.dpi*c
            zpl.add_field_origin(int(x_start+(c*x_offset)), int(y_start))
            zpl.add_field_data(text[:14])
            zpl.add_field_origin(int(x_start + x_offset+(c*x_offset)), int(y_start + y_offset*2.5))
            bc = Code128_Barcode(f'{barcode}', 'N', 30, 'Y')
            zpl.add_barcode(bc)

        zpl.add_print_quantity(int(quantity/self.columns))
        
        printer = NetworkPrinter(self.ipaddress)
        printer.print_zpl(zpl)

if __name__=='__main__':
    lm = Label_Maker(ipaddress = sys.argv[1], fontsize=int(sys.argv[4]))
    lm.printlabel(sys.argv[2],sys.argv[3])