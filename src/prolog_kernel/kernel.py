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

    prolog_version = ""
    banner = "Prolog kernel"
    cells = {}
    last_code = ""
    notebookName = ""
    cellId = ""
    preamble = ""
    fileName = ""
    moduleName = ""
    dirName = ""
    absoluteFileName = ""
    preambleLength = 0

    #process = Popen(['agda', '--interaction'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    process = None # pexpect.spawnu('swipl')

    firstTime = True

    def startProlog(self):

        self.process = pexpect.spawnu('swipl')

        #if self.firstTime:
        if True:
            self.print(f'Waiting for prolog to start...')

            # skip to the 4th "?- "
            '''
            Welcome to SWI-Prolog (threaded, 64 bits, version 8.0.3)
            SWI-Prolog comes with ABSOLUTELY NO WARRANTY. This is free software.
            Please run ?- license. for legal details.

            For online help and background, visit http://www.swi-prolog.org
            For built-in help, use ?- help(Topic). or ?- apropos(Word).
            '''

            #for i in range(4):
            self.process.expect_exact('\n?- ') # process.expect takes a regular expression instead

            self.print(f'Prolog shell started!')
            self.firstTime = False
        return

    def stopProlog(self):

        if not (self.process is None):
            self.process.terminate(force=True)
            self.process = None

    def readPrologVersion(self):
        # swipl --version
        # SWI-Prolog version 8.0.3 for x86_64-darwin
        p = pexpect.spawn('swipl --version')
        p.expect(pexpect.EOF)
        result = str(p.before)
        tokens = result.split(" ")
        version = tokens[2] # remove initial "SWI-Prolog version "
        #version = version[:-5] # remove trailing "\r\n"
        self.print(f'Detected Prolog version: {version}')
        return version

    def __init__(self, **kwargs):
        Kernel.__init__(self, **kwargs)
        self.prolog_version = self.readPrologVersion()

    def interact(self, cmd):

        self.startProlog()

        self.print("Interacting with Prolog: %s" % cmd)

        self.process.sendline(cmd)
        self.process.expect_exact('\n?- ', timeout=120)
        result = self.process.before

        # TODO: when there is an error as below, we need to look for "?" and send "a\n"
        '''
        ERROR: No permission to load source `'/Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl'' (Non-module file already loaded into module user; trying to load into test)
        ERROR: In:
        ERROR:   [22] throw(error(permission_error(load,source,'/Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl'),context(...,'Non-module file already loaded into module user; trying to load into test')))
        ERROR:   [20] '$assert_load_context_module'('/Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl',test,[expand(false),...]) at /usr/local/Cellar/swi-prolog/8.0.3_1/libexec/lib/swipl/boot/init.pl:2589
        ERROR:   [19] '$mt_do_load'(<clause>(0x7fd1bfe84370),test,'/Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl',test,[expand(false),...]) at /usr/local/Cellar/swi-prolog/8.0.3_1/libexec/lib/swipl/boot/init.pl:2186
        ERROR:   [18] setup_call_catcher_cleanup(system:with_mutex('$load_file',...),system:'$mt_do_load'(<clause>(0x7fd1bfe84370),test,'/Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl',test,...),_10992,system:'$mt_end_load'(<clause>(0x7fd1bfe84370))) at /usr/local/Cellar/swi-prolog/8.0.3_1/libexec/lib/swipl/boot/init.pl:468
        ERROR:   [15] '$load_file'(test,test,[expand(false),...]) at /usr/local/Cellar/swi-prolog/8.0.3_1/libexec/lib/swipl/boot/init.pl:2074
        ERROR:    [7] <user>
        ERROR:
        ERROR: Note: some frames are missing due to last-call optimization.
        ERROR: Re-run your program in debug mode (:- debug.) to get more detail.
        ^  Call: (20) call(system:'$mt_end_load'(<clause>(0x7fd1bfe84370))) ? abort
        '''

        self.print(f'Prolog replied: {result}')

        #skip the first line (it's a copy of cmd)
        result = result[result.index('\n')+1:]
        result = result.strip() # remove whitespaces and newlines from beginning and end

        #result = result.decode()
        

        #result = {}
        # TODO: ad parsing of errors and warnings such as

        '''
        Warning: /Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl:5:
            Singleton variables: [X]
        ERROR: /Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl:5:
            catch/3: Undefined procedure: p/1
            However, there are definitions for:
                    p/2
        Warning: /Users/lorenzo/Google Drive/dev/prolog-kernel/test.pl:5:
            Goal (directive) failed: user:p(_9850)
        '''

        self.stopProlog()
        return result

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

    def getModuleName(self, code):
        code = self.removeComments(code)
        lines = code.split('\n')

        #look for the first line matching ":- module(MODULENAME)."
        for line in lines:
            match = re.search(r':- *module *\(([a-zA-Z0-9.\-]*), *\[.*\]\) *\.', line)
            if match:
                moduleName = match.group(1)
                self.print(f'Detected module: {moduleName}')
                return moduleName

        self.print(f'No module detected')
        return ""

    def getFileName(self, code):
        moduleName = self.getModuleName(code)
        return moduleName + ".pl" if moduleName != "" else ""

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

        self.fileName = self.getFileName(code)
        self.dirName = self.getDirName(code)
        self.moduleName = self.getModuleName(code)
        self.absoluteFileName = os.path.abspath(self.fileName)
        self.preambleLength = 0
        error = False

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
            else:
                self.preamble = ":- module(test)."

        self.print(f'detected fileName: {self.fileName}, dirName: {self.dirName}, moduleName: {self.moduleName}, notebookName: {self.notebookName}, cellId: {self.cellId}, preamble: {self.preamble}')

        # use the provided preamble only if the module name is missing
        #if fileName == "":

            # if no line \"module [modulename] where\" is provided,
            # we create a standard one ourselves
        #    preambleLength = len(preamble.split("\n")) - 1
        #    new_code = preamble + code

        #    fileName = self.getFileName(new_code)
        #    dirName = self.getDirName(new_code)
        #    moduleName = self.getModuleName(new_code)
        #    absoluteFileName = os.path.abspath(fileName)
        #    self.print(f'redetected fileName: {fileName}, dirName: {dirName}, moduleName: {moduleName}, notebookName: {notebookName}, cellId: {cellId}, new code: {new_code}')

        #    code = new_code

        if self.moduleName != "":
            lines = code.split('\n')
            numLines = len(lines)

            #self.print("file: %s" % fileName)

            if self.dirName != "" and not os.path.exists(self.dirName):
                os.makedirs(self.dirName)

            fileHandle = open(self.fileName, "w+")

            for i in range(numLines):
                fileHandle.write("%s\n" % lines[i])

            fileHandle.close()

            query = f'[{self.moduleName}].\n'
            result = self.interact(query)

            if result == "":
                result = "OK"

            #save the result of the last evaluation
            self.cells[self.fileName] = result

            # save the code that was executed
            self.code = code

        else:
            error = True
            result = 'The first line of a cell code should be of the form ":- module(module_name, [... exported symbols ...])."'

        if not silent:
            stream_content = {'name': 'stdout', 'text': result}
            try:
                self.send_response(self.iopub_socket, 'stream', stream_content)
            except AttributeError: # during testing there is no such method, just ignore
                self.print("Ignoring call to self.send_response")

        user_expressions = {
            "fileName": self.absoluteFileName,
            "moduleName": self.moduleName,
            "preambleLength" : self.preambleLength,
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