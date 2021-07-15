#!/usr/bin/env python

__author__ = "David Rickett"
__credits__ = ["David Rickett"]
__license__ = "MIT"
__version__ = "1.0.1"
__maintainer__ = "David Rickett"
__email__ = "dap.rickett@gmail.com"
__status__ = "Production"

import re
import sys
from simple_zpl2 import ZPLDocument, Code128_Barcode, NetworkPrinter

class LabelMaker:

    INCH=25.4 #1 inch = 25.4mm
    
    #what these translate to in linear cm
    DPI203 = 203
    DPI300 = 300

    def __init__(self, ipaddress: str, port: int = 9100, metric: bool = False, dpi: int = 203,
                width: float = 1, height: float = 0.5, margins: float = (1/16),
                columns: int = 1, fontsize: int = 30, description: str = '', location: str = ''):
        """
        Setup a ethernet enabled Zebra printer.
        
        Default dimensions correspond to Uline S-22370 1 x 1/2" labels.

        Use millimeters or inches for dimensions, if metric is specified it will be converted to inch internally.

        :param str ipaddress: IP Address of printer.
        :param int port: TCP port of printer, default 9100.
        :param bool metric: Whether dimensions of label media is in mm (true) or inch (false).
        :param int dpi: Use 203 DPI or 300 DPI.
        :param float width: Width of label, default 1 inch.
        :param float height: Height of label, default 0.5 inch.
        :param float margins: Gap between labels if columns > 1, default 1/16 inch.
        :param int columns: Number of columns, default 1.
        :param int fontsize: Size of font measured in dots-per-inch, default 30 dots.
        :param str description: Brief description of printer.
        :param str location: Brief description of location of printer.
        """

        self.margins = margins
        self.ipaddress = ipaddress
        self.port = port
        self.dpi = dpi
        self.columns = columns
        self.metric = metric
        self.fontsize = fontsize
        self.description = description
        self.location = location
        self.height = height
        self.width = width

        #convert to inches for internal measurements, otherwise the rest gets iffy
        if self.metric:
            self.height = height / self.INCH
            self.width = width / self.INCH

    def __generateTemplates(self):
        pass

    def __storeTemplates(self):
        pass

    def getinfo(self):
        """A JSON object describing the printer."""
        return {'description': self.description, 'location': self.location, 'size': f'{self.width}x{self.height}', 'width': self.width, 'height': self.height, 'columns': self.columns}

    def metric(self, metric: bool = False):
        """Set standard of measurement
        
        :param bool metric: Set True for metric measurements, set False for imperial."""
        self.metric = metric

    def columns(self, columns: int = 1):
        """Set number of columns.
        
        :param int columns: Set number of columns, will be clamped to 1 or greater."""
        self.columns = max(1, columns)

    def width(self, width: float = 1.0):
        """Set width of print media.
        
        :param float width: New width of media, minimum value is .5 inch or 12mm"""
        self.width = min(0.5, width)
        if self.metric:
            self.width = max(self.INCH/2, width / self.INCH)

    def height(self, height: float = 0.5):
        """Set height of print media.
        
        :param float height: New height of media, minimum value is .5 inch or 12mm"""
        self.height = min(0.5,height)
        if self.metric:
            self.height = max(self.INCH/2, height / self.INCH)

    def printReplacementLabel(self, text: str, barcode: str = '', quantity: int = 12):
        """
        Prints barcoded labels.
        
        :param str text: Text to be printed on label.
        :param str barcode: Barcode to be printed on label.
        :param int quantity: Quantity of labels to be printed. Quantity will be divided by columns of media and truncated.
        """
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

    def printPriceLabel(self, text: str, subtext: str = '', sku: str = '',
                        barcode: str = '', quantity: int = 1, price: float = 0.00,
                        priceWithoutTax: float = 0.00, deposit: float = 0.00):
        """
        Prints barcoded labels. Layout intended for 2x1" media.
        
        :param str text: Text to be printed on label.
        :param str subtext: Subtext to be printed on label.
        :param str sku: SKU to be printed on label.
        :param str barcode: Barcode to be printed on label.
        :param int quantity: Quantity of labels to be printed. Quantity will be divided by columns of media and truncated.
        :param float price: Final price of item.
        :param float priceWithoutTax: Price of item without sales tax.
        :param float deposit: Bottle deposit of item.
        """

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
            zpl.add_field_data(text)

            zpl.add_field_origin(int(x_start+(c*x_offset)), int(y_start)+self.fontsize+3)
            zpl.add_font('0',character_height=self.fontsize/2)
            zpl.add_field_data(sku)
            
            zpl.add_field_origin(int(x_start+(c*x_offset)), int(y_start)+self.fontsize+self.fontsize/2+6)
            zpl.add_field_block(width=self.width/3, max_lines=2, dots_between_lines=3)
            zpl.add_font('0',character_height=self.fontsize/3)
            zpl.add_field_data(subtext, True)

            zpl.add_

            zpl.add_field_origin(int(x_start_bc + x_offset+(c*x_offset)), int(y_start + y_offset*2.5))
            bc = Code128_Barcode(f'{barcode}', 'N', 25, 'Y')
            zpl.add_barcode(bc)

        zpl.add_print_quantity(int(int(quantity)/self.columns))
        
        printer = NetworkPrinter(self.ipaddress,self.port)
        printer.print_zpl(zpl)

if __name__=='__main__':
    lm = LabelMaker(ipaddress = sys.argv[1], fontsize=int(sys.argv[4]))
    lm.printReplacementLabel(sys.argv[2],sys.argv[3])