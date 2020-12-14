import re

class lineitem:

    def __init__(self, *vars, linestring='', **kwargs):

        if isinstance(vars, tuple):
            vars = list(vars)

        if vars is None and len(linestring) > 0 and type(linestring) == str:
            vars = linestring.split(',')

        #if vars is not none and doesn't match our expected data, throw exception
        if vars is not None and len(vars) < 6:
            raise Exception()

        print(vars, len(vars))

        #ordernumber, orderdate, sku, upc, productdescription, sellingunitsize, uom, qty, thirdparty

        self.details = {}
        self.details['sku']             = int(vars.pop(0)   or kwargs.get('sku',-1))                    #int
        self.details['upc']             = int(vars.pop(0)   or kwargs.get('upc',-1))                    #int
        self.details['productdescription']        = (vars.pop(0)   or kwargs.get('productdescription',"default value"))  #str
        if len(vars) > 3:              #if there are more list members than there should be, assume some numpty at LDB put a comma in an item name.
            self.details['proddesc']    += vars.pop(0)
        self.details['sellingunitsize'] = (vars.pop(0)   or kwargs.get('sellingunitsize',"default value"))   #str
        self.details['uom']             = (vars.pop(0)   or kwargs.get('uom',"default value"))       #str
        self.details['qty']             = int(float(vars.pop(0)   or kwargs.get('qty',0)))                     #int

        #we remove 'illegal' characters in the main script, but its always handy to do it again
        for k,v in self.details.items():
            if type(v) == str:
                v = re.sub('([^ \sa-zA-Z0-9.]| {2,})','',v)
        print(self.details)

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
                retstr += f"'{v}',"
            else:
                retstr += f'{v},'
        return retstr[:-1]

    def getall(self):
        return self.details

    def get(self, key):
        return self.details[key]

if __name__ == "__main__":
    stri = "123456,1234567890,description,750mL,CS,12"
    li = lineitem( *stri.split(',') )
    query = f'INSERT INTO orderlog ({li.getkeysconcat()}) VALUES ({li.getvaluesconcat()})'
    print(query)
