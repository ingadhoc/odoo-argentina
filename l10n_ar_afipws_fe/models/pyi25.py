# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
import os
import sys
from PIL import Image, ImageDraw
__author__ = "Mariano Reingart <reingart@gmail.com>"
__copyright__ = "Copyright (C) 2011 Mariano Reingart"
__license__ = "GPL 3.0"
__version__ = "1.02c"


class PyI25:
    "Interfaz para generar PDF de Factura Electr�nica"
    _public_methods_ = ['GenerarImagen',
                        'DigitoVerificadorModulo10'
                        ]
    _public_attrs_ = ['Version', 'Excepcion', 'Traceback']

    _reg_progid_ = "PyI25"
    _reg_clsid_ = "{5E6989E8-F658-49FB-8C39-97C74BC67650}"

    def __init__(self):
        self.Version = __version__
        self.Exception = self.Traceback = ""

    def GenerarImagen(self, codigo, archivo="barras.png",
                      basewidth=3, width=None, height=30, extension="PNG"):
        "Generar una im�gen con el c�digo de barras Interleaved 2 of 5"
        # basado de:
        #  * http://www.fpdf.org/en/script/script67.php
        #  * http://code.activestate.com/recipes/426069/

        wide = basewidth
        narrow = basewidth / 3

        # c�digos ancho/angostos (wide/narrow) para los d�gitos
        bars = ("nnwwn", "wnnnw", "nwnnw", "wwnnn", "nnwnw", "wnwnn", "nwwnn",
                "nnnww", "wnnwn", "nwnwn", "nn", "wn")

        # agregar un 0 al principio si el n�mero de d�gitos es impar
        if len(codigo) % 2:
            codigo = "0" + codigo

        if not width:
            width = (len(codigo) * 3) * basewidth + (10 * narrow)
            # width = 380
        # crear una nueva im�gen
        im = Image.new("1", (width, height))

        # agregar c�digos de inicio y final
        codigo = "::" + codigo.lower() + ";:"   # A y Z en el original

        # crear un drawer
        draw = ImageDraw.Draw(im)

        # limpiar la im�gen
        draw.rectangle(((0, 0), (im.size[0], im.size[1])), fill=256)

        xpos = 0
        # dibujar los c�digos de barras
        for i in range(0, len(codigo), 2):
            # obtener el pr�ximo par de d�gitos
            bar = ord(codigo[i]) - ord("0")
            space = ord(codigo[i + 1]) - ord("0")
            # crear la sequencia barras (1er d�gito=barras, 2do=espacios)
            seq = ""
            for s in range(len(bars[bar])):
                seq = seq + bars[bar][s] + bars[space][s]

            for s in range(len(seq)):
                if seq[s] == "n":
                    width = narrow
                else:
                    width = wide

                # dibujar barras impares (las pares son espacios)
                if not s % 2:
                    draw.rectangle(
                        ((xpos, 0), (xpos + width - 1, height)), fill=0)
                xpos = xpos + width

        im.save(archivo, extension.upper())
        return True

    def DigitoVerificadorModulo10(self, codigo):
        "Rutina para el c�lculo del d�gito verificador 'm�dulo 10'"
        # http://www.consejo.org.ar/Bib_elect/diciembre04_CT/documentos/rafip1702.htm
        # Etapa 1: comenzar desde la izquierda, sumar todos los caracteres
        # ubicados en las posiciones impares.
        codigo = codigo.strip()
        if not codigo or not codigo.isdigit():
            return ''
        etapa1 = sum([int(c) for i, c in enumerate(codigo) if not i % 2])
        # Etapa 2: multiplicar la suma obtenida en la etapa 1 por el n�mero 3
        etapa2 = etapa1 * 3
        # Etapa 3: comenzar desde la izquierda, sumar todos los caracteres que
        # est�n ubicados en las posiciones pares.
        etapa3 = sum([int(c) for i, c in enumerate(codigo) if i % 2])
        # Etapa 4: sumar los resultados obtenidos en las etapas 2 y 3.
        etapa4 = etapa2 + etapa3
        # Etapa 5: buscar el menor n�mero que sumado al resultado obtenido en
        # la etapa 4 d� un n�mero m�ltiplo de 10. Este ser� el valor del d�gito
        # verificador del m�dulo 10.
        digito = 10 - (etapa4 - (int(etapa4 / 10) * 10))
        if digito == 10:
            digito = 0
        return str(digito)


if __name__ == '__main__':

    if "--register" in sys.argv or "--unregister" in sys.argv:
        import win32com.server.register
        win32com.server.register.UseCommandLine(PyI25)
    elif "py2exe" in sys.argv:
        from distutils.core import setup
        from nsis import build_installer
        # import py2exe
        setup(
            name="PyI25",
            version=__version__,
            description="Interfaz PyAfipWs I25 %s",
            long_description=__doc__,
            author="Mariano Reingart",
            author_email="reingart@gmail.com",
            url="http://www.sistemasagiles.com.ar",
            license="GNU GPL v3",
            com_server=[
                {'modules': 'pyi25', 'create_exe': False, 'create_dll': True},
            ],
            console=['pyi25.py'],
            options={
                'py2exe': {
                    'includes': [],
                    'optimize': 2,
                    'excludes': [
                        "pywin", "pywin.dialogs", "pywin.dialogs.list",
                        "win32ui", "distutils.core", "py2exe", "nsis"],
                }},
            data_files=[(".", ["licencia.txt"]), ],
            cmdclass={"py2exe": build_installer}
        )
    else:

        pyi25 = PyI25()

        if '--barras' in sys.argv:
            barras = sys.argv[sys.argv.index("--barras") + 1]
        else:
            cuit = 20267565393
            tipo_cbte = 2
            punto_vta = 4001
            cae = 61203034739042
            fch_venc_cae = 20110529

            # codigo de barras de ejemplo:
            barras = '%11s%02d%04d%s%8s' % (
                cuit, tipo_cbte, punto_vta, cae, fch_venc_cae)

        if '--noverificador' not in sys.argv:
            barras = barras + pyi25.DigitoVerificadorModulo10(barras)

        if '--archivo' in sys.argv:
            archivo = sys.argv[sys.argv.index("--archivo") + 1]
            extension = os.path.splitext(archivo)[1]
            extension = extension.upper()[1:]
            if extension == 'JPG':
                extension = 'JPEG'
        else:
            archivo = "prueba-cae-i25.png"
            extension = 'PNG'

        pyi25.GenerarImagen(barras, archivo, extension=extension)

        if '--mostrar' not in sys.argv:
            pass
        elif sys.platform == "linux2":
            os.system("eog ""%s""" % archivo)
        else:
            os.startfile(archivo)
