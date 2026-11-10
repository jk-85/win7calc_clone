import math
import random
import unittest
from classiccalc.mathlib import D,PI,E,CalcError,binary,evaluate,factorial,format_number,number,root,unary


class MathTests(unittest.TestCase):
    def near(self,a,b,tol='1e-45'):self.assertLessEqual(abs(a-D(b)),D(tol)*max(D(1),abs(D(b))))
    def test_sin_30(self):self.near(unary('sin',D(30)),'.5')
    def test_cos_60(self):self.near(unary('cos',D(60)),'.5')
    def test_tan_45(self):self.near(unary('tan',D(45)),'1')
    def test_sin_pi(self):self.assertEqual(unary('sin',PI,'Radians'),0)
    def test_sin_gradians(self):self.assertEqual(unary('sin',D(100),'Gradians'),1)
    def test_asin(self):self.near(unary('asin',D('.5')),'30')
    def test_acos(self):self.near(unary('acos',D('.5')),'60')
    def test_atan(self):self.near(unary('atan',D(1)),'45')
    def test_atan_negative(self):self.near(unary('atan',D(-1)),'-45')
    def test_atan_large(self):self.near(unary('atan',D('1e50')),'90')
    def test_tan_90_error(self):
        with self.assertRaises(CalcError):unary('tan',D(90))
    def test_ln_e(self):self.near(unary('ln',E),1)
    def test_log(self):self.assertEqual(unary('log',D(1000)),3)
    def test_exp(self):self.near(unary('exp',D(1)),E)
    def test_cuberoot_negative(self):self.near(unary('cuberoot',D(-27)),-3)
    def test_root_negative_even(self):
        with self.assertRaises(CalcError):root(D(-16),D(4))
    def test_factorial(self):self.assertEqual(factorial(D(20)),D(2432902008176640000))
    def test_zero_factorial(self):self.assertEqual(factorial(D(0)),1)
    def test_factorial_invalid(self):
        for v in (D(-1),D('1.5'),D(99999)):
            with self.assertRaises(CalcError):factorial(v)
    def test_reciprocal(self):self.assertEqual(unary('reciprocal',D(4)),D('.25'))
    def test_dms(self):self.assertEqual(unary('dms',D('12.5')),D('12.3'))
    def test_degrees(self):self.assertEqual(unary('degrees',D('12.3')),D('12.5'))
    def test_dms_roundtrip(self):self.near(unary('degrees',unary('dms',D('-12.3456789'))),'-12.3456789')
    def test_frac(self):self.assertEqual(unary('frac',D('-2.5')),D('-.5'))
    def test_sinh_inverse(self):self.near(unary('asinh',unary('sinh',D('1.25'))),'1.25')
    def test_cosh_inverse(self):self.near(unary('acosh',unary('cosh',D('1.25'))),'1.25')
    def test_tanh_inverse(self):self.near(unary('atanh',unary('tanh',D('.75'))),'.75')
    def test_bad_domains(self):
        for name,x in [('sqrt',-1),('log',0),('ln',-1),('asin',2),('acos',-2),('acosh',0),('atanh',1),('reciprocal',0)]:
            with self.subTest(name=name):
                with self.assertRaises(CalcError):unary(name,D(x))
    def test_trig_random_against_math(self):
        rng=random.Random(99)
        for _ in range(100):
            value=rng.uniform(-700,700)
            for func in ('sin','cos'):
                self.near(unary(func,D(str(value)),'Radians'),str(getattr(math,func)(value)),tol='1e-12')
    def test_formatter_zero(self):self.assertEqual(format_number(D('-0.0000')),'0')
    def test_formatter_integer(self):self.assertEqual(format_number(D('123.00000')),'123')
    def test_formatter_grouping(self):self.assertEqual(format_number(D('1234567.89'),grouping=True),'1,234,567.89')
    def test_formatter_exponent(self):self.assertEqual(format_number(D('1e100')),'1e100')
    def test_formatter_precision(self):self.assertEqual(format_number(PI),'3.1415926535897932384626433832795')
    def test_parser_precedence(self):self.assertEqual(evaluate('2+3*4'),14)
    def test_parser_immediate(self):self.assertEqual(evaluate('2+3*4',immediate=True),20)
    def test_parser_parentheses(self):self.assertEqual(evaluate('(2+3)*4'),20)
    def test_parser_functions(self):self.near(evaluate('sin(30)+cos(60)'),1)
    def test_parser_factorial(self):self.assertEqual(evaluate('5!'),120)
    def test_parser_percent(self):self.assertEqual(evaluate('50%'),D('.5'))
    def test_parser_unary_precedence(self):self.assertEqual(evaluate('-2^2'),-4)
    def test_parser_negative_exponent(self):self.assertEqual(evaluate('2^-3'),D('.125'))
    def test_parser_scientific_notation(self):self.assertEqual(evaluate('1.2e-3 + 4.5e2'),D('450.0012'))
    def test_parser_root(self):self.near(evaluate('27 root 3'),3)
    def test_parser_history_labels(self):self.assertEqual(evaluate('square(3)+cube(2)'),17)
    def test_parser_rejects_code(self):
        for text in ["__import__('os').system('echo bad')","open('/tmp/x')","1;2","[1][0]","NaN","Infinity","2**3","a",'sin(2','2+','']:
            with self.subTest(text=text):
                with self.assertRaises(CalcError):evaluate(text)
    def test_parser_length_bound(self):
        with self.assertRaises(CalcError):evaluate('1+'*4000+'1')
    def test_parser_depth_bound(self):
        with self.assertRaises(CalcError):evaluate('('*100+'1'+')'*100)
    def test_zero_division(self):
        with self.assertRaises(CalcError):binary('/',D(1),D(0))
    def test_invalid_number(self):
        for v in ('NaN','Infinity','abc','1e100000'):
            with self.assertRaises(CalcError):number(v)
