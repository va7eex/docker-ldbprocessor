import re
import sys
from simple_zpl2 import ZPLDocument, Code128_Barcode, NetworkPrinter

class LabelMaker:

    INCH=2.54
    
    #what these translate to in linear cm
    DPI203 = 203
    DPI300 = 300

    def __init__(self, ipaddress: str, port: int = 9100, metric: bool = False, dpi: int = 203,
                width: float = 1, height: float = 0.5, margins: float = (1/16),
                columns: int = 2, fontsize: int = 30, description: str = ''):
        #note: we're defaulting to uline S-10765 dimensions
        self.height = height
        self.width = width
        self.margins = margins
        self.ipaddress = ipaddress
        self.port = port
        self.dpi = dpi
        self.columns = columns
        self.metric=metric
        self.fontsize=fontsize
        self.description = description

    def getinfo(self):
        return {'description': self.description, 'size': f'{self.width}x{self.height}', 'width': self.width, 'height': self.height, 'columns': self.columns}

    def printlabel(self, text: str, barcode: str = '', quantity: int = 12):
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

        zpl.add_print_quantity(int(int(quantity)/self.columns))
        
        printer = NetworkPrinter(self.ipaddress,self.port)
        printer.print_zpl(zpl)

if __name__=='__main__':
    lm = LabelMaker(ipaddress = sys.argv[1], fontsize=int(sys.argv[4]))
    lm.printlabel(sys.argv[2],sys.argv[3])