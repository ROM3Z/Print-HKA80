class Util():
  def DoValueDouble(self, value):
      listItemsCount = len(value)
      integerValue=int(value[0:-2])
      floatingValue=value[(listItemsCount-2):]
      decimals=float(floatingValue)/100
      totalAmount= integerValue + decimals
      return totalAmount