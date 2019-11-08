from ipykernel.kernelbase import Kernel
import re
import subprocess
import os
from IPython.utils.tokenutil import token_at_cursor, line_at_cursor
from subprocess import Popen, PIPE, STDOUT
import pexpect

class PrologKernel(Kernel):
    implementation = 'prolog'
    implementation_version = '0.1'
    language = 'prolog'
    language_version = '1.0'
    language_info = {
        'name': 'prolog',
        'mimetype': 'text/prolog',
        'file_extension': '.pl',
    }

    banner = "Prolog kernel"
    cells = {}
    last_code = ""

    prolog_version = ""

    notebookName = ""
    cellId = ""
    preamble = ""

    #process = Popen(['agda', '--interaction'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    #process = pexpect.spawnu('agda --interaction')

    #firstTime = True

    #def startAgda(self):
    #    if self.firstTime:
    #        self.process.expect('Agda2> ')
    #        self.firstTime = False
    #    return

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        #self.agda_version = self.readAgdaVersion()

    # return line and column of an position in a string
    def line_of(self, s, n):

        lines = s.split('\n')
        
        i = 0 # current line
        j = 0 # cumulative length

        found = False

        for line in lines:

            if n >= j and n <= j + len(line):
                found = True
                break

            # self.print(f'line {i} has length {len(line)}, cumulative {j}')

            i += 1
            j += len(line) + 1 # need to additionally record the '\n'

        if found:
            return i, n - j
        else:
            return -1, -1

    def getSrcFileName(self, code):

        code = self.removeComments(code)
        lines = code.split('\n')

        #look for the first line matching ":- module(MODULENAME)"
        for line in lines:
            if bool(re.match(r':- *module([a-zA-Z0-9.\-]*) *', line)):
                # fileName = "tmp/" + re.sub(r"-- *", "", firstLine)
                moduleName = re.sub(r'module *( *', "", line) # delete prefix
                moduleName = re.sub(r' * ) *', "", moduleName) # delete suffix

                return moduleName

        return ""

    def getFileName(self, code):

        moduleName = self.getModuleName(code)
        return moduleName.replace(".", "/") + ".pl" if moduleName != "" else ""

    def getDirName(self, code):

        moduleName = self.getModuleName(code)
        last = moduleName.rfind(".")
        prefixName = moduleName[:last]
        return prefixName.replace(".", "/") if last != -1 else ""

    def do_shutdown(self, restart):
        return

    def do_execute(self, code, silent, store_history=True, user_expressions=None, allow_stdin=False):

        fileName = self.getFileName(code)
        dirName = self.getDirName(code)
        moduleName = self.getModuleName(code)
        absoluteFileName = os.path.abspath(fileName)

        preambleLength = 0

        self.print(f'user_expressions: {user_expressions}')
        self.print(f'executing code: {code}')

        if user_expressions:
            # get notebook name (if any)
            if "notebookName" in user_expressions:
                self.notebookName = user_expressions["notebookName"]

            # get cell id
            if "cellId" in user_expressions:
                self.cellId = user_expressions["cellId"]

            if "preamble" in user_expressions:
                self.preamble = user_expressions["preamble"]
            else
                self.preamble = ":- module(test)."

        notebookName = self.notebookName
        cellId = self.cellId
        preamble = self.preamble

        self.print(f'detected fileName: {fileName}, dirName: {dirName}, moduleName: {moduleName}, notebookName: {notebookName}, cellId: {cellId}, preamble: {preamble}')

        # use the provided preamble only if the module name is missing
        if fileName == "":

            # if no line \"module [modulename] where\" is provided,
            # we create a standard one ourselves
            preambleLength = len(preamble.split("\n")) - 1
            new_code = preamble + code

            fileName = self.getFileName(new_code)
            dirName = self.getDirName(new_code)
            moduleName = self.getModuleName(new_code)
            absoluteFileName = os.path.abspath(fileName)
            self.print(f'redetected fileName: {fileName}, dirName: {dirName}, moduleName: {moduleName}, notebookName: {notebookName}, cellId: {cellId}, new code: {new_code}')

            code = new_code

        self.fileName = fileName
        lines = code.split('\n')
        numLines = len(lines)

        #self.print("file: %s" % fileName)

        if dirName != "" and not os.path.exists(dirName):
            os.makedirs(dirName)

        fileHandle = open(fileName, "w+")

        for i in range(numLines):
            fileHandle.write("%s\n" % lines[i])

        fileHandle.close()

        #subprocess.run(["agda", fileName])
        #result = os.popen("agda %s" % fileName).read()

        outputFileName = "./output.txt"

        os.system(f"swipl {fileName} > {outputFileName} 2>&1")
        
        l = open(outputFileName, 'r')
        result = l.readlines()[:-8] # skip the last 8 lines
        
        if result == "":
            result = "OK"

        #save the result of the last evaluation
        self.cells[fileName] = result

        # save the code that was executed
        self.code = code

        if not silent:
            stream_content = {'name': 'stdout', 'text': result}
            try:
                self.send_response(self.iopub_socket, 'stream', stream_content)
            except AttributeError: # during testing there is no such method, just ignore
                self.print("Ignoring call to self.send_response")

        user_expressions = {
            "fileName": absoluteFileName,
            "moduleName": moduleName,
            "preambleLength" : preambleLength,
            "isError": error
        }

        return {'status': 'ok' if not error else 'error',
                # The base class increments the execution count
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': user_expressions,
               }
        
    # triggered by SHIFT+TAB
    def do_inspect(self, code, cursor_pos, detail_level=0):

        self.print(f'do_inspect cursor_pos: {cursor_pos}, selection: "{code}" of length {len(code)}, code: "{self.code}" of length {len(self.code)}')

        # do nothing for now
        return {'status': 'ok', 'found': True, 'data': {'text/plain': ""}}

    # triggered by TAB
    # handle unicode completion here
    def do_complete(self, code, cursor_pos):

        #self.print(f'considering code: {code}, pos: {cursor_pos}')

        half_subst = {
            'Nat' : 'ℕ',
            '<=<>' : '≤⟨⟩',
            '<==<>' : '≤≡⟨⟩',
            '=<>' : '≡⟨⟩',
            '-><>' : '↝<>',
            '->*<>' : '↝*<>',
            'top' : '⊤',
            'bot' : '⊥',
            'neg' : '¬',
            '/\\' : '∧',
            '\\/' : '∨',
            '\\' : 'λ', # it is important that this comes after /\
            'Pi' : 'Π',
            'Sigma' : 'Σ',
            '->' : '→',
            '→' :  '↦',
            '↦' : '↝',
            '↝' : '->',
            '=>' : '⇒',
            '<' : '⟨',
            '>' : '⟩', # it is important that this comes after ->
            '⟩' : '≻',
            '≻' : '>',
            'forall' : '∀',
            'exists' : '∃',
            'A' : '𝔸',
            'B' : '𝔹',
            'C' : 'ℂ',
            'N' : 'ℕ',
            'Q' : 'ℚ',
            'R' : 'ℝ',
            'Z' : 'ℤ',
            ':=' : '≔',
            '/=' : '≢',
            'leq' : '≤',
            '<=' : '≤',
            'geq' : '≥',
            '>=' : '≥',
            '=' : '≡',
            '[=' : '⊑',
            'alpha' : 'α',
            'beta' : 'β',
            'gamma' : 'γ',
            'rho' : 'ρ',
            'e' : 'ε',
            'mu' : 'μ',
            'xor' : '⊗',
            'emptyset' : '∅',
            'qed' : '∎',
            '.' : '·',
            'd' : '∇',
            'Delta' : 'Δ',
            'delta' : 'δ',
            'notin' : '∉',
            'in' : '∈',
            '[' : '⟦',
            ']' : '⟧',
            '::' : '∷',
            '0' : '𝟬', # '𝟢',
            '𝟬' : '₀',
            '₀' : '0',
            '1' : '𝟭', # '𝟣'
            '𝟭' : '₁',
            '₁' : '1',
            '2' : '₂',
            '3' : '₃',
            '4' : '₄',
            '5' : '₅',
            '6' : '₆',
            '7' : '₇',
            '8' : '₈',
            '9' : '₉',
            '+' : '⨁',
            '~' : '≈',
            'x' : '×',
            'o' : '∘',
            'phi' : 'φ',
            'psi' : 'ψ',
            'xi' : 'ξ',
            #'??' : "{! !}",
            'iff' : '⟺',
            'w'  : 'ω ',
            'omega' : 'ω',
            'Gamma' : 'Γ',
            'tau' : 'τ',
            'sigma' : 'σ',
            #';' : ';', very bad idea: the second semicolon lloks the same but it is a different unicode symbol...
            ';' : '⨟',
            '(' : '⟬',
            ')' : '⟭',
            'b' : 'ᵇ',
            'empty' : '∅',
            '|-' : '⊢',
            'models' : '⊨',
            '|=' : '⊨',
            'cup' : '⊔',
            'l' : 'ℓ',
            'op' : 'ᵒᵖ',
            '{{' : '⦃',
            '}}' : '⦄'
        }

        other_half = {val : key for (key, val) in half_subst.items() if val not in list(half_subst.keys())}
        subst = {**half_subst, **other_half} # merge the two dictionaries
        keys = [key for (key, val) in subst.items()]

        length = len(code)
        matches = []
        error = False

        for key in keys:
            n = len(key)
            cursor_start = cursor_pos - n
            cursor_end = cursor_pos
            s = code[cursor_start:cursor_pos]

            if s == key:
                # we have a match
                matches = [subst[key]]
                break
    
        return {'matches': matches, 'cursor_start': cursor_start,
                'cursor_end': cursor_end, 'metadata': {},
                'status': 'ok' if not error else 'error'}

    def removeComments(self, code):

        level = 0
        i = 0
        length = len(code)
        result = ""

        while i < length:
            if level == 0 and code[i:i+2] == "%": # skip till the end of the line
                while i < length and code[i] != "\n":
                    i += 1

                result += "\n" if code[i:i+1] == "\n" else ""
            #elif code[i:i+2] == "{-":
            #    level += 1
            #    i += 1
            #elif code[i:i+2] == "-}" and level > 0:
            #    level -= 1
            #    i += 1
            elif level == 0:
                result += code[i]

            i += 1

        return result

    def print(self, msg):
        try:
            self.log.error(msg)
        except AttributeError:
            print(msg)

def escapify(s):
    # escape quotations, new lines
    result = s.replace("\"", "\\\"").replace("\n", "\\n")
    return result

def deescapify(s):
     # go back
    result = s.replace("\\\"", "\"").replace("\\n", "\n")
    return result