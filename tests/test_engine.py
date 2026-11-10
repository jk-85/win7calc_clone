import random
import unittest
from decimal import Decimal
from classiccalc.engine import Calculator
from classiccalc.mathlib import D, CalcError


def enter(c, text):
    if str(text).startswith('-'):
        enter(c,str(text)[1:]);c.sign();return
    for digit in str(text):c.input_digit(digit)


def sequence(mode,*items):
    c=Calculator(mode)
    for item in items:
        if item in ('+','-','*','/','mod','^','root','and','or','xor','lsh','rsh'):c.operator(item)
        elif item=='=':c.equals()
        elif item=='%':c.percent()
        elif item=='(':c.parenthesis()
        elif item==')':c.parenthesis(True)
        else:enter(c,item)
    return c


class StandardTests(unittest.TestCase):
    def test_decimal_exact(self):self.assertEqual(sequence('Standard','0.1','+','0.2','=').value,D('.3'))
    def test_left_to_right(self):self.assertEqual(sequence('Standard','2','+','3','*','4','=').value,20)
    def test_repeat_equals(self):self.assertEqual(sequence('Standard','8','+','5','=','=').value,18)
    def test_missing_rhs(self):self.assertEqual(sequence('Standard','8','+','=').value,16)
    def test_replace_operator(self):self.assertEqual(sequence('Standard','8','+','*','2','=').value,16)
    def test_add_percent(self):self.assertEqual(sequence('Standard','200','+','10','%','=').value,220)
    def test_subtract_percent(self):self.assertEqual(sequence('Standard','200','-','10','%','=').value,180)
    def test_multiply_percent(self):self.assertEqual(sequence('Standard','200','*','10','%','=').value,20)
    def test_divide_percent(self):self.assertEqual(sequence('Standard','200','/','10','%','=').value,2000)
    def test_ce_preserves_pending(self):
        c=sequence('Standard','12','+','45');c.clear_entry();enter(c,'8');c.equals();self.assertEqual(c.value,20)
    def test_clear_does_not_clear_memory(self):
        c=sequence('Standard','42');c.memory_action('MS');c.clear();c.memory_action('MR');self.assertEqual(c.value,42)
    def test_memory_add_subtract(self):
        c=sequence('Standard','10');c.memory_action('MS');c.clear();enter(c,'3');c.memory_action('M+');c.memory_action('M-')
        c.memory_action('MR');self.assertEqual(c.value,10);c.memory_action('MC');self.assertFalse(c.memory_set)
    def test_backspace(self):
        c=sequence('Standard','123.45');c.backspace();self.assertEqual(c.entry,'123.4')
    def test_backspace_result_noop(self):
        c=sequence('Standard','12','+','3','=');c.backspace();self.assertEqual(c.value,15)
    def test_error_recovery(self):
        c=Calculator();c.set_error('Cannot divide by zero');c.input_digit('5');self.assertEqual(c.value,5);self.assertFalse(c.error)
    def test_new_calculation_after_equals(self):
        c=sequence('Standard','2','+','3','=');enter(c,'4');self.assertEqual(c.value,4);self.assertFalse(c.tokens)
    def test_continue_result(self):self.assertEqual(sequence('Standard','2','+','3','=','*','2','=').value,10)
    def test_negative_zero_input(self):
        c=Calculator();c.sign();enter(c,'5');self.assertEqual(c.value,-5)
    def test_history_limit(self):
        c=Calculator()
        for i in range(230):c.clear();enter(c,str(i));c.equals()
        self.assertEqual(len(c.history),200);self.assertEqual(c.history[0]['result'],'30')
    def test_digit_limit(self):
        c=Calculator();enter(c,'1'*40);self.assertEqual(len(c.entry),32)
    def test_paste_safe_expression(self):
        c=Calculator('Scientific');c.paste('sqrt(81)+2^3');self.assertEqual(c.value,17)
    def test_paste_grouped_number(self):
        c=Calculator();c.paste('1,234,567.89');self.assertEqual(c.value,D('1234567.89'))
    def test_paste_decimal_comma(self):
        c=Calculator();c.paste('1,25');self.assertEqual(c.value,D('1.25'))
    def test_zero_memory_flag(self):
        c=Calculator();c.memory_action('MS');self.assertTrue(c.memory_set)


class ScientificTests(unittest.TestCase):
    def test_precedence(self):self.assertEqual(sequence('Scientific','2','+','3','*','4','=').value,14)
    def test_parentheses(self):self.assertEqual(sequence('Scientific','(','2','+','3',')','*','4','=').value,20)
    def test_nested_parentheses(self):self.assertEqual(sequence('Scientific','2','*','(','3','+','(','4','*','5',')',')','=').value,46)
    def test_autoclose(self):self.assertEqual(sequence('Scientific','2','*','(','3','+','4','=').value,14)
    def test_implicit_multiply(self):self.assertEqual(sequence('Scientific','2','(','3','+','4',')','=').value,14)
    def test_operator_after_group(self):self.assertEqual(sequence('Scientific','(','2','+','3',')','+','4','=').value,9)
    def test_unary_after_group(self):
        c=sequence('Scientific','(','4','+','5',')');c.function('sqrt');c.equals();self.assertEqual(c.value,3)
    def test_nested_unary_group(self):
        c=sequence('Scientific','2','*','(','4','+','5',')');c.function('sqrt');c.equals();self.assertEqual(c.value,6)
    def test_power_right_associative(self):self.assertEqual(sequence('Scientific','2','^','3','^','2','=').value,512)
    def test_exponent_sign(self):
        c=Calculator('Scientific');enter(c,'1.5');c.exponent();c.sign();enter(c,'3');self.assertEqual(c.value,D('.0015'))
    def test_incomplete_exponent(self):
        c=Calculator('Scientific');enter(c,'3');c.exponent();self.assertEqual(c.value,3)
    def test_sine(self):
        c=Calculator('Scientific');enter(c,'30');c.function('sin');self.assertLess(abs(c.value-D('.5')),D('1e-55'))
    def test_percent_in_expression(self):self.assertEqual(sequence('Scientific','100','+','20','%','=').value,120)
    def test_nested_percent_base(self):
        self.assertEqual(sequence('Scientific','2','*','(','200','+','300','+','10','%',')','=').value,1100)
    def test_entry_not_in_expression_line(self):
        c=sequence('Scientific','2');self.assertEqual(c.expression,'')
        c.operator('+');enter(c,'3');self.assertEqual(c.expression,'2 +')
    def test_history(self):
        c=sequence('Scientific','2','+','3','*','4','=');self.assertEqual(c.history[0]['result'],'14')


class ProgrammerTests(unittest.TestCase):
    def setUp(self):self.c=Calculator('Programmer')
    def test_int_division(self):self.assertEqual(sequence('Programmer','9','/','2','=').value,4)
    def test_negative_division(self):self.assertEqual(sequence('Programmer','-9','/','2','=').value,-4)
    def test_negative_mod(self):self.assertEqual(sequence('Programmer','-9','mod','2','=').value,-1)
    def test_base_conversion(self):
        enter(self.c,'255');self.c.set_radix(16);self.assertEqual(self.c.display,'FF')
        self.c.set_radix(2);self.assertEqual(self.c.display,'11111111')
        self.c.set_radix(8);self.assertEqual(self.c.display,'377')
    def test_byte_wrap(self):
        self.c.set_bits(8);enter(self.c,'127');self.c.operator('+');enter(self.c,'1');self.c.equals();self.assertEqual(self.c.value,-128)
    def test_signed_hex(self):
        self.c.set_bits(8);self.c.set_radix(16);enter(self.c,'FF');self.c.set_radix(10);self.assertEqual(self.c.value,-1)
    def test_not(self):self.c.function('not');self.assertEqual(self.c.value,-1)
    def test_rotate(self):
        self.c.set_bits(8);enter(self.c,'128');self.c.function('rol');self.assertEqual(self.c.value,1)
        self.c.function('ror');self.assertEqual(self.c.value,-128)
    def test_logical_shift(self):self.assertEqual(sequence('Programmer','-1','rsh','1','=').value,(1<<63)-1)
    def test_shift_large(self):self.assertEqual(sequence('Programmer','1','lsh','64','=').value,0)
    def test_and(self):self.assertEqual(sequence('Programmer','15','and','6','=').value,6)
    def test_or(self):self.assertEqual(sequence('Programmer','10','or','5','=').value,15)
    def test_xor(self):self.assertEqual(sequence('Programmer','15','xor','6','=').value,9)
    def test_precedence(self):self.assertEqual(sequence('Programmer','2','+','3','*','4','=').value,14)
    def test_64bit_integer_precision(self):
        enter(self.c,'9223372036854775806');self.c.operator('+');enter(self.c,'1');self.c.equals();self.assertEqual(self.c.value,9223372036854775807)
    def test_overflow_64(self):
        enter(self.c,'9223372036854775807');self.c.operator('+');enter(self.c,'1');self.c.equals();self.assertEqual(self.c.value,-9223372036854775808)
    def test_toggle_bit(self):
        self.c.toggle_bit(63);self.assertEqual(self.c.value,-9223372036854775808)
        self.c.toggle_bit(0);self.assertEqual(self.c.value,-9223372036854775807)
    def test_disabled_digits(self):
        self.c.set_radix(2);self.c.input_digit('2');self.assertEqual(self.c.value,0)
    def test_paste_prefix(self):self.c.paste('0xDEADBEEF');self.assertEqual(self.c.value,3735928559)
    def test_paste_overflow(self):
        self.c.set_bits(8)
        with self.assertRaises(CalcError):self.c.paste('256')
    def test_width_preserves_pending(self):
        enter(self.c,'255');self.c.operator('+');self.c.set_bits(8);enter(self.c,'1');self.c.equals();self.assertEqual(self.c.value,0)
    def test_random_wrapped_arithmetic(self):
        rng=random.Random(11235)
        for bits in (8,16,32,64):
            for _ in range(80):
                a=rng.randrange(-(1<<(bits-1)),1<<(bits-1));b=rng.randrange(-(1<<(bits-1)),1<<(bits-1))
                for op,expected in (('+',a+b),('-',a-b),('*',a*b),('and',a&b),('or',a|b),('xor',a^b)):
                    self.c.set_bits(bits)
                    self.assertEqual(self.c._binary(op,a,b),self.c.normalize(expected))


class StatisticsTests(unittest.TestCase):
    def setUp(self):
        self.c=Calculator('Statistics');self.c.samples=list(map(D,[2,4,4,4,5,5,7,9]))
    def test_mean(self):self.c.statistic('mean');self.assertEqual(self.c.value,5)
    def test_sum(self):self.c.statistic('sum');self.assertEqual(self.c.value,40)
    def test_mean_square(self):self.c.statistic('mean_square');self.assertEqual(self.c.value,29)
    def test_sum_square(self):self.c.statistic('sum_square');self.assertEqual(self.c.value,232)
    def test_population(self):self.c.statistic('population_sd');self.assertEqual(self.c.value,2)
    def test_sample(self):
        self.c.statistic('sample_sd');self.assertLess(abs(self.c.value-(D(32)/7).sqrt()),D('1e-55'))
    def test_empty(self):
        self.c.samples=[]
        with self.assertRaises(CalcError):self.c.statistic('mean')
    def test_single_sample(self):
        self.c.samples=[D(1)]
        with self.assertRaises(CalcError):self.c.statistic('sample_sd')
    def test_add_starts_new_entry(self):
        self.c.clear();enter(self.c,'12');self.c.add_sample();enter(self.c,'5');self.assertEqual(self.c.value,5)
