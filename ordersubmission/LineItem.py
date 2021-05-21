import re
#from schema import Schema, And, Use, Optional, SchemaError

class LineItem:

    def __init__(self, linestring='', *vars, **kwargs):
#        self.schema = Schema(None)
        self.details = {}
        pass

    def __len__(self):
        return len(self.details)

    def getkeys(self):
        return list(self.details.keys())

    def getkeysconcat(self):
        retstr = ''
        for k in self.getkeys():
            retstr += f'{k},'
        return retstr[:-1]

    def getvalues(self):
        return list(self.details.values())

    def getvaluesconcat(self):
        retstr = ''
        for v in self.getvalues():
            if type(v) == str:
                retstr += f'\'{v}\','
            else:
                retstr += f'{v},'
        return retstr[:-1]

    def getall(self, urlsafe=False):
        if urlsafe:
            urlsafedata = {}
            for key, value in self.details.items():
                urlsafedata[key] = f'{value}'
            return urlsafedata
        return self.details
        #return self.schema.validate(self.details)

    def get(self, key):
        return self.details[key]

    def __sanitize(self):
        #we remove 'illegal' characters in the main script, but its always handy to do it again
        for k,v in self.details.items():
            if type(v) == str:
                v = re.sub(r'([^ \sa-zA-Z0-9.]| {2,})','',v)
#            print(f'{k}: {v}')
            if type(v) == int or type(v) == float:
                v = abs(v)
        
        print(self.details)

class LineItemAR(LineItem):

    def __init__(self, *vars, **kwargs):

#        self.schema = Schema({'sku': int, 'productdescription': str, 'productcategory': str,
#                              'size': str, 'qty': int, 'uom': str, 'priceperuom': float,
#                              'extendedprice': float, 'suquantity': int, 'suprice': float,
#                              'wppsavings': float, 'contdeposit': float, 'refnum': int})

        if isinstance(vars, tuple):
            vars = list(vars)

        #if vars is None and len(linestring) > 0 and type(linestring) == str:
        #    vars = linestring.split(',')

        print(vars, len(vars))

        #if vars is not none and doesn't match our expected data, throw exception
        if not kwargs and vars is not None and len(vars) < 13:
            raise Exception()

        if vars:
            self.details = {} 
            self.details['sku']                     = int(vars.pop(0))                    #int
            self.details['productdescription']      = (vars.pop(0))  #str
            if len(vars) > 11:              #if there are more list members than there should be, assume some numpty at LDB put a comma in an item name.
                self.details['productdescription']  += vars.pop(0)
            self.details['productcategory']         = vars.pop(0)   #str
            self.details['size']                    = vars.pop(0)      #str
            self.details['qty']                     = int(float(vars.pop(0)))                     #int
            self.details['uom']                     = vars.pop(0)       #str
            self.details['priceperuom']             = float(vars.pop(0))           #float
            self.details['extendedprice']           = float(vars.pop(0))              #float
            self.details['suquantity']              = int(float(vars.pop(0)))              #int unsigned
            self.details['suprice']                 = float(vars.pop(0))               #float
            self.details['wppsavings']              = float(vars.pop(0))                  #float
            self.details['contdeposit']             = float(vars.pop(0))                 #float
            self.details['refnum']                  = int(float(vars.pop(0)))                    #int

        if kwargs:
            self.details = {} 
            self.details['sku']                 = int(kwargs.get('sku',-1))                    #int
            self.details['productdescription']  = kwargs.get('productdescription',"default value")  #str
            self.details['productcategory']     = kwargs.get('productcategory',"default value")   #str
            self.details['size']                = kwargs.get('size',"default value")      #str
            self.details['qty']                 = int(float(kwargs.get('qty',0)))                     #int
            self.details['uom']                 = kwargs.get('uom',"default value")       #str
            self.details['priceperuom']         = float(kwargs.get('priceperuom',0.0))           #float
            self.details['extendedprice']       = float(kwargs.get('extendedprice',0.0))              #float
            self.details['suquantity']          = int(float(kwargs.get('suquantity',0)))              #int unsigned
            self.details['suprice']             = float(kwargs.get('suprice',0.0))               #float
            self.details['wppsavings']          = float(kwargs.get('wppsavings',0.0))                  #float
            self.details['contdeposit']         = float(kwargs.get('contdeposit',0.0))                 #float
            self.details['refnum']              = int(float(kwargs.get('refnum',-1)))                    #int

        self.__sanitize()

    def __sanitize(self):
        #we remove 'illegal' characters in the main script, but its always handy to do it again
        for k,v in self.details.items():
            if type(v) == str:
                v = re.sub(r'([^ \sa-zA-Z0-9.]| {2,})','',v)
#            print(f'{k}: {v}')
            if type(v) == int or type(v) == float:
                v = abs(v)
        
        print(self.details)

class LineItemOS(LineItem):

    def __init__(self, *vars, **kwargs):

#        self.schema = Schema({'sku': int, 'upc': int, 'productdescription': str,
 #                             'sellingunitsize': str, 'uom': str, 'qty': int})

        if isinstance(vars, tuple):
            vars = list(vars)

        #if vars is not none and doesn't match our expected data, throw exception
        if not kwargs and vars is not None and len(vars) < 13:
            raise Exception()

        #ordernumber, orderdate, sku, upc, productdescription, sellingunitsize, uom, qty, thirdparty

        if vars:
            self.details = {}
            self.details['sku']                     = int(vars.pop(0))                    #int
            self.details['upc']                     = int(vars.pop(0))                    #int
            self.details['productdescription']      = vars.pop(0)  #str
            if len(vars) > 3:              #if there are more list members than there should be, assume some numpty at LDB put a comma in an item name.
                self.details['productdescription']  += vars.pop(0)
            self.details['sellingunitsize']         = vars.pop(0)   #str
            self.details['uom']                     = vars.pop(0)       #str
            self.details['qty']                     = int(float(vars.pop(0)))                     #int

        if kwargs:
            self.details = {}
            self.details['sku']                 = int(kwargs.get('sku',-1))                    #int
            self.details['upc']                 = int(kwargs.get('upc',-1))                    #int
            self.details['productdescription']  = kwargs.get('productdescription',"default value")  #str
            self.details['sellingunitsize']     = kwargs.get('sellingunitsize',"default value")   #str
            self.details['uom']                 = kwargs.get('uom',"default value")      #str
            self.details['qty']                 = int(float(kwargs.get('qty',0)))                     #int
        
        self.__sanitize()

    def __sanitize(self):
        #we remove 'illegal' characters in the main script, but its always handy to do it again
        for k,v in self.details.items():
            if type(v) == str:
                v = re.sub(r'([^ \sa-zA-Z0-9.]| {2,})','',v)
#            print(f'{k}: {v}')
            if type(v) == int or type(v) == float:
                v = abs(v)
        
        print(self.details)
    

if __name__ == "__main__":
    stri = "123456,description,category,750mL,12,215.88,17.99,1,12,0.0,0.0,1.20,654321"
    li = LineItemAR( *stri.split(',') )
    print(li.getkeysconcat())
    print(li.getvaluesconcat())
    query = f'INSERT INTO invoicelog ({li.getkeysconcat()}) VALUES ({li.getvaluesconcat()})'
    print(query)
