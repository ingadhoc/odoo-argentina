UNIDADES = (
    '',
    'UN ',
    'DOS ',
    'TRES ',
    'CUATRO ',
    'CINCO ',
    'SEIS ',
    'SIETE ',
    'OCHO ',
    'NUEVE ',
    'DIEZ ',
    'ONCE ',
    'DOCE ',
    'TRECE ',
    'CATORCE ',
    'QUINCE ',
    'DIECISEIS ',
    'DIECISIETE ',
    'DIECIOCHO ',
    'DIECINUEVE ',
    'VEINTE '
)

DECENAS = (
    'VENTI',
    'TREINTA ',
    'CUARENTA ',
    'CINCUENTA ',
    'SESENTA ',
    'SETENTA ',
    'OCHENTA ',
    'NOVENTA ',
    'CIEN '
)

CENTENAS = (
    'CIENTO ',
    'DOSCIENTOS ',
    'TRESCIENTOS ',
    'CUATROCIENTOS ',
    'QUINIENTOS ',
    'SEISCIENTOS ',
    'SETECIENTOS ',
    'OCHOCIENTOS ',
    'NOVECIENTOS '
)

def to_word(number):
    ans = to_word_int(int(number)) + ' PESOS'
    centavos = int((number - int(number)) * 100)
    if centavos > 0:
        ans += ' CON ' + to_word_int(centavos) + ' CENTAVOS'
    return ans.title()
    

def to_word_int(number):
    """
    Converts a number into string representation
    """
    converted = ''
    
    if number == 0:
        return 'CERO '
        
    if not (0 < number < 999999999):
        return 'No es posible convertir el numero a letras'
 
    number_str = str(number).zfill(9)
    millones = number_str[:3]
    miles = number_str[3:6]
    cientos = number_str[6:]
 
    if(millones):
        if(millones == '001'):
            converted += 'UN MILLON'
        elif(int(millones) > 0):
            converted += '%sMILLONES' % __convertNumber(millones)
 
    if(miles):
        if(miles == '001'):
            converted += 'MIL '
        elif(int(miles) > 0):
            converted += '%sMIL' % __convertNumber(miles)
 
    if(cientos):
        if(cientos == '001'):
            converted += 'UN '
        elif(int(cientos) > 0):
            converted += '%s' % __convertNumber(cientos)
 
    #converted += 'PESOS'
 
    #return converted.title()
    return converted
 
def __convertNumber(n):
    """
    Max length must be 3 digits
    """
    output = ''
 
    if(n == '100'):
        output = "CIEN "
    elif(n[0] != '0'):
        output = CENTENAS[int(n[0])-1]
 
    k = int(n[1:])
    if(k <= 20):
        output += UNIDADES[k]
    else:
        if((k > 30) & (n[2] != '0')):
            output += '%sY %s' % (DECENAS[int(n[1])-2], UNIDADES[int(n[2])])
        else:
            output += '%s%s' % (DECENAS[int(n[1])-2], UNIDADES[int(n[2])])
 
    return output
