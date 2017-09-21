##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2017 Christoph Rackwitz <christoph.rackwitz@rwth-aachen.de>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

'''
Morse PD.
'''

import sigrokdecode as srd

def decode_ditdah(s):
    return tuple( {'-': 3, '.': 1}[c] for c in s )

def encode_ditdah(tpl):
    return ''.join({1:'.', 3:'-'}[c] for c in tpl)

# https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.1677-1-200910-I!!PDF-E.pdf
# Recommendation ITU-R M.1677-1
# (10/2009)
# International Morse code
alphabet = {
    # 1.1.1 Letters
    '.-':       'a',
    '-...':     'b',
    '-.-.':     'c',
    '-..':      'd',
    '.':        'e',
    '..-..':    'é', # "accented"
    '..-.':     'f',
    '--.':      'g',
    '....':     'h',
    '..':       'i',
    '.---':     'j',
    '-.-':      'k',
    '.-..':     'l',
    '--':       'm',
    '-.':       'n',
    '---':      'o',
    '.--.':     'p',
    '--.-':     'q',
    '.-.':      'r',
    '...':      's',
    '-':        't',
    '..-':      'u',
    '...-':     'v',
    '.--':      'w',
    '-..-':     'x',
    '-.--':     'y',
    '--..':     'z',

    # 1.1.2 Figures
    '.----':    '1',
    '..---':    '2',
    '...--':    '3',
    '....-':    '4',
    '.....':    '5',
    '-....':    '6',
    '--...':    '7',
    '---..':    '8',
    '----.':    '9',
    '-----':    '0',

    # 1.1.3 Punctuation marks and miscellaneous signs 
    '.-.-.-':   '.',          # Full stop (period)
    '--..--':   ',',          # Comma
    '---...':   ':',          # Colon or division sign
    '..--..':   '?',          # Question mark (note of interrogation or request for repetition of a transmission not understood)
    '.----.':   '’',          # Apostrophe
    '-....-':   '-',          # Hyphen or dash or subtraction sign
    '-..-.':    '/',          # Fraction bar or division sign
    '-.--.':    '(',          # Left-hand bracket (parenthesis)
    '-.--.-':   ')',          # Right-hand bracket (parenthesis)
    '.-..-.':   '“ ”',        # Inverted commas (quotation marks) (before and after the words)
    '-...-':    '=',          # Double hyphen
    '...-.':    'UNDERSTOOD', # Understood
    '........': 'ERROR',      # Error (eight dots)
    '.-.-.':    '+',          # Cross or addition sign
    '.-...':    'WAIT',       # Wait
    '...-.-':   'EOW',        # End of work
    '-.-.-':    'START',      # Starting signal (to precede every transmission)
    '.--.-.':   '@',          # Commercial at

    #'-.-':      'ITT',        # K: Invitation to transmit

    # 3.2.1 For the multiplication sign, the signal corresponding to the letter X shall be transmitted. 
    #'-..-':     '×',          # Multiplication sign
}

alphabet = { decode_ditdah(k): v for k,v in alphabet.items() }

# 2 Spacing and length of the signals 
# (right side is just for printing)
symbols = { # level, time units
    # 2.1 A dash is equal to three dots. 
    (1, 1): '*',
    (1, 3): '===',
    # 2.2 The space between the signals forming the same letter is equal to one dot. 
    (0, 1): '_',
    # 2.3 The space between two letters is equal to three dots. 
    (0, 3): '__',
    # 2.4 The space between two words is equal to seven dots. 
    (0, 7): '___',
}


class Decoder(srd.Decoder):
    api_version = 3
    id = 'morse'
    name = 'Morse'
    longname = 'Morse Code PD'
    desc = 'Decodes demodulated Morse Code'
    license = 'gplv2+'

    inputs = ['logic']
    outputs = ['morse']
    channels = (
        { 'id': 'data', 'name': 'Data', 'desc': 'Data line' },
    )
    options = (
        { 'id': 'timeunit', 'desc': 'Time Unit (guess)', 'default': 0.1 },
    )
    annotations = (
        ('time', 'Time'),
        ('units', 'Units'),
        ('symbol', 'Symbol'),
        ('letter', 'Letter'),
        ('word', 'Word'),
    )
    annotation_rows = tuple((u,v,(i,)) for i,(u,v) in enumerate(annotations))

    def __init__(self):
        pass
        self.samplerate = None # None -> no timing output

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.out_binary = self.register(srd.OUTPUT_BINARY)
        #self.out_meta = self.register(srd.OUTPUT_META)

    def decode_symbols(self):
        'annotate symbols, emit symbols, handle timeout via token'

        timeunit = self.options['timeunit']
        if self.samplerate is None:
            self.samplerate = 1.0

        self.wait({0: 'r'})
        prevtime = self.samplenum # time of an actual edge

        while True:
            (val,) = self.wait([{0: 'e'}, {'skip': int(5 * self.samplerate * timeunit)}])

            pval = 1-val
            curtime = self.samplenum
            dt = (curtime - prevtime) / self.samplerate
            units = dt / timeunit
            iunits = round(units)
            error = abs(units - iunits)

            symbol = (pval, iunits)

            if self.matched[1]:
                yield None # flush word
                continue

            self.put(prevtime, curtime, self.out_ann, [0, ['{:.3g}'.format(dt)]])
            self.put(prevtime, curtime, self.out_ann, [1, ['{:.1f}*{:.3g}'.format(units, timeunit)]])

            if symbol in symbols:
                yield (prevtime, curtime, symbol)

            prevtime = curtime

            thisunit = dt / iunits
            timeunit += (thisunit - timeunit) * 0.02 * iunits # adapt

    def decode_morse(self):
        'group symbols into letters'
        sequence = ()
        s0 = s1 = None

        for item in self.decode_symbols():
            do_yield = False

            if item is not None: # level + width
                (t0, t1, symbol) = item
                (sval, sunits) = symbol

                if sval == 1:
                    if s0 is None: s0 = t0
                    s1 = t1
                    sequence += (sunits,)
                else:
                    # generate "flush" for end of letter, end of word
                    if sunits >= 3:
                        do_yield = True

            else:
                do_yield = True

            if do_yield:
                if sequence:
                    yield (s0, s1, alphabet.get(sequence, encode_ditdah(sequence)))
                    sequence = ()
                    s0 = s1 = None

            if item is None:
                yield None # pass through flush of 5+ space

    def decode(self):
        'annotate letters, group into words'
        s0 = s1 = None
        word = ''
        for item in self.decode_morse():
            do_yield = False

            if item is not None: # append letter
                (t0, t1, letter) = item
                self.put(t0, t1, self.out_ann, [3, [letter]])

                if s0 is None: s0 = t0
                s1 = t1
                word += letter

            else:
                do_yield = True

            if do_yield: # flush of word
                if word:
                    self.put(s0, s1, self.out_ann, [4, [word]])
                    word = ''
                    s0 = s1 = None

