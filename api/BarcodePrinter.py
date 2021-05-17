import re
import sys
from simple_zpl2 import ZPLDocument, Code128_Barcode, NetworkPrinter

class LabelMaker:

    INCH=25.4
    
    #what these translate to in linear cm
    DPI203 = 203
    DPI300 = 300

    def __init__(self, ipaddress: str, port: int = 9100, metric: bool = False, dpi: int = 203,
                width: float = 1, height: float = 0.5, margins: float = (1/16),
                columns: int = 2, fontsize: int = 30, description: str = '', location: str = ''):
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
        self.location = location

        if self.metric:
            raise TypeError('Use imperial for this')

    def getinfo(self):
        return {'description': self.description, 'location': self.location, 'size': f'{self.width}x{self.height}', 'width': self.width, 'height': self.height, 'columns': self.columns}

    def printlabel(self, text: str, barcode: str = '', quantity: int = 12):
        zpl = ZPLDocument()
        
        x_start = self.margins*self.dpi
        x_start_bc = self.margins*self.dpi
        y_start = self.margins*2*self.dpi
        x_offset = self.dpi * (1/16)
        y_offset = self.dpi * (1/16)

        zpl.add_default_font('0', character_height=self.fontsize)

        #small labels can't fit normal default-width barcodes (module_width=2) in simple_zpl2
        if(self.width <= 1):
            zpl.add_barcode_default(module_width=1)

        for c in range(self.columns):

            x_start += (self.width+self.margins)*self.dpi*c
            x_start_bc += (self.width+self.margins)*self.dpi*c
            zpl.add_field_origin(int(x_start+(c*x_offset)), int(y_start))
            zpl.add_field_data(text[:14])
            zpl.add_field_origin(int(x_start_bc + x_offset+(c*x_offset)), int(y_start + y_offset*2.5))

            bc = Code128_Barcode(f'{barcode}', 'N', 25, 'Y')
            zpl.add_barcode(bc)

        zpl.add_print_quantity(int(int(quantity)/self.columns))
        
        printer = NetworkPrinter(self.ipaddress,self.port)
        printer.print_zpl(zpl)

if __name__=='__main__':
    lm = LabelMaker(ipaddress = sys.argv[1], fontsize=int(sys.argv[4]))
    lm.printlabel(sys.argv[2],sys.argv[3])