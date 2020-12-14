import re

class lineitem:

    def __init__(self, *vars, linestring='', **kwargs):

        if isinstance(vars, tuple):
            vars = list(vars)

        if vars is None and len(linestring) > 0 and type(linestring) == str:
            vars = linestring.split(',')

        #if vars is not none and doesn't match our expected data, throw exception
        if vars is not None and len(vars) < 13:
            raise Exception()

        print(vars, len(vars))

        self.details = {}
        self.details['sku']             = int(vars.pop(0)   or kwargs.get('sku',-1))                    #int
        self.details['proddesc']        = (vars.pop(0)   or kwargs.get('proddesc',"default value"))  #str
        if len(vars) > 11:              #if there are more list members than there should be, assume some numpty at LDB put a comma in an item name.
            self.details['proddesc']    += vars.pop(0)
        self.details['prodcat']         = (vars.pop(0)   or kwargs.get('prodcat',"default value"))   #str
        self.details['size']            = (vars.pop(0)   or kwargs.get('size',"default value"))      #str
        self.details['qty']             = int(float(vars.pop(0)   or kwargs.get('qty',0)))                     #int
        self.details['uom']             = (vars.pop(0)   or kwargs.get('uom',"default value"))       #str
        self.details['priceperuom']     = float(vars.pop(0) or kwargs.get('priceperuom',0.0))           #float
        self.details['extprice']        = float(vars.pop(0) or kwargs.get('extprice',0.0))              #float
        self.details['suquantity']      = int(float(vars.pop(0)   or kwargs.get('suquantity',0)))              #int unsigned
        self.details['suprice']         = float(vars.pop(0) or kwargs.get('suprice',0.0))               #float
        self.details['wpps']            = float(vars.pop(0) or kwargs.get('wpps',0.0))                  #float
        self.details['contd']           = float(vars.pop(0) or kwargs.get('contd',0.0))                 #float
        self.details['refnum']             = int(float(vars.pop(0)   or kwargs.get('refnum',-1)))                    #int

        #we remove 'illegal' characters in the main script, but its always handy to do it again
        for k,v in self.details.items():
            if type(v) == str:
                v = re.sub('([^ \sa-zA-Z0-9.]| {2,})','',v)
#            print(f'{k}: {v}')
        print(self.details)

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
    stri = "123456,description,category,750mL,12,215.88,17.99,1,12,0.0,0.0,1.20,654321"
    li = lineitem( *stri.split(',') )
    print(li.getkeysconcat())
    print(li.getvaluesconcat())
    query = f'INSERT INTO invoicelog ({li.getkeysconcat()}) VALUES ({li.getvaluesconcat()})'
    print(query)
