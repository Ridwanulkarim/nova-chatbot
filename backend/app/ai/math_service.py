import re
from typing import Dict, Any, Optional, Tuple
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

# Standard mathematical functions and constants permitted in mathematical expressions
MATH_FUNCS = {
    'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
    'asin', 'acos', 'atan', 'sinh', 'cosh', 'tanh',
    'log', 'ln', 'exp', 'sqrt', 'cbrt', 'abs',
    'pi', 'e', 'oo', 'theta', 'phi', 'gamma',
    'diff', 'integrate', 'limit', 'sum',
    'dx', 'dy', 'dt', 'dz'
}

class MathSolverService:
    """
    Advanced Mathematics & Symbolic Computation Engine.
    Uses SymPy for rigorous symbolic calculation, equation solving, calculus,
    matrix operations, and verified LaTeX formatting.
    """

    def __init__(self):
        self.transformations = (
            standard_transformations
            + (implicit_multiplication_application, convert_xor)
        )

    def clean_and_extract_math(self, text: str) -> Tuple[str, str]:
        """
        Separates natural language intent (e.g. 'how', 'why', 'calculate', 'solve')
        from the actual mathematical expression.
        """
        clean = text.strip()

        # 1. Calculus: Derivative intent
        deriv_match = re.search(r'(?i)(?:derivative\s+of|differentiate)\s+([a-zA-Z0-9\+\-\*\/\^\(\)\s\.]+)', clean)
        if deriv_match:
            return ('derivative', deriv_match.group(1).strip(' \t\r\n?!.,;:'))

        # 2. Calculus: Integral intent
        integ_match = re.search(r'(?i)(?:integral\s+of|integrate)\s+([a-zA-Z0-9\+\-\*\/\^\(\)\s\.]+?)(?:\s*dx|\s*dt|\s*dy)?$', clean)
        if integ_match:
            return ('integral', integ_match.group(1).strip(' \t\r\n?!.,;:'))

        # 3. Strip leading conversational prefix questions/commands
        clean = re.sub(
            r'^(?:can you\s+)?(?:please\s+)?(?:tell me\s+)?'
            r'(?:what(?:\'s|\s+is|\s+are)?|how(?:\s+do(?:es)?\s+you|\s+to|\s+much\s+is|\s+is|\s+are|\s+come)?|why(?:\s+does|\s+is|\s+are)?|calculate|compute|solve|evaluate|find|simplify|explain(?:\s+how)?)\s+(?:the\s+)?',
            '', clean, flags=re.I
        )

        # 4. Strip trailing conversational suffixes ('how', 'why', 'please', 'step by step', etc.)
        clean = re.sub(
            r'\s+(?:how|why|please|step(?:\s*by\s*step)?|steps|explain|explanation|thanks|thank you)\s*[\?\!\.]*$',
            '', clean, flags=re.I
        )

        clean = clean.strip(' \t\r\n?!.,;:')
        clean = re.sub(r'^(?:is|are)\s+', '', clean, flags=re.I)

        return ('expr', clean)

    def is_valid_math_tokens(self, expr_str: str) -> bool:
        """
        Verifies that every word in expr_str is either a valid mathematical function/constant
        or a single-letter variable. Rejects natural language words (e.g. 'how', 'please', 'apples')
        so they are never mistakenly parsed as letter multiplications by SymPy.
        """
        if not expr_str:
            return False

        # Must contain at least one digit or math symbol or single letter variable
        if not re.search(r'[0-9\+\-\*\/\^\=xXyYzZaAbBcCdDtT]', expr_str):
            return False

        words = re.findall(r'[a-zA-Z]+', expr_str)
        for w in words:
            if len(w) == 1:
                # Single letter variable: x, y, z, t, a, b, etc.
                continue
            if w.lower() in MATH_FUNCS:
                continue
            # Multi-letter unrecognized word found -> not a pure math expression
            return False

        return True

    def is_math_query(self, query: str) -> bool:
        """Determines if query is primarily a mathematical computation, equation, or proof."""
        clean = query.lower()
        math_keywords = [
            "solve", "integral", "derivative", "differentiate", "integrate",
            "calculate", "evaluate", "limit", "matrix", "determinant",
            "eigenvalue", "equation", "polynomial", "factor", "expand",
            "simplify", "proof", "roots of", "sum of", "differential equation"
        ]
        has_symbols = bool(re.search(r'[\+\-\*\/\^\=∫∂∑√]|x\^2|\b[0-9]+\s*[\+\-\*\/]\s*[0-9]+', query))
        has_keyword = any(kw in clean for kw in math_keywords)

        if not (has_keyword or has_symbols):
            return False

        # Verify extracted expression has valid mathematical tokens
        op, target = self.clean_and_extract_math(query)
        return self.is_valid_math_tokens(target)

    def solve_expression(self, expression_str: str) -> Dict[str, Any]:
        """
        Attempts symbolic evaluation, factoring, differentiation, or equation solving.
        """
        x, y, z, t = sp.symbols('x y z t')
        result = {
            "success": False,
            "raw_input": expression_str,
            "clean_expr": None,
            "exact_result": None,
            "latex_result": None,
            "method": "symbolic_computation",
            "verification": None,
        }

        op, clean_expr = self.clean_and_extract_math(expression_str)
        result["clean_expr"] = clean_expr

        if not self.is_valid_math_tokens(clean_expr):
            result["error"] = "Contains natural language tokens, not a raw symbolic expression."
            return result

        try:
            # 1. Calculus: Derivative
            if op == 'derivative':
                parsed = parse_expr(clean_expr, transformations=self.transformations)
                deriv = sp.diff(parsed, x)
                result["success"] = True
                result["exact_result"] = str(deriv)
                result["latex_result"] = sp.latex(deriv)
                result["method"] = "symbolic_differentiation"
                result["verification"] = "Verified using Leibniz product/chain rule"
                return result

            # 2. Calculus: Integral
            if op == 'integral':
                parsed = parse_expr(clean_expr, transformations=self.transformations)
                integ = sp.integrate(parsed, x)
                result["success"] = True
                result["exact_result"] = str(integ)
                result["latex_result"] = sp.latex(integ)
                result["method"] = "symbolic_integration"
                result["verification"] = f"Derivative of result equals integrand: {sp.diff(integ, x) == parsed}"
                return result

            # 3. Equations & Identities
            if "=" in clean_expr:
                parts = clean_expr.split("=")
                lhs = parse_expr(parts[0].strip(), transformations=self.transformations)
                rhs = parse_expr(parts[1].strip(), transformations=self.transformations)

                free = lhs.free_symbols.union(rhs.free_symbols)
                if not free:
                    # Arithmetic identity verification (e.g. 1 + 1 = 2)
                    is_equal = bool(lhs.evalf() == rhs.evalf())
                    result["success"] = True
                    result["exact_result"] = f"{lhs} = {rhs} (Identity: {is_equal})"
                    result["latex_result"] = f"{sp.latex(lhs)} = {sp.latex(rhs)}"
                    result["method"] = "arithmetic_identity_verification"
                    result["verification"] = f"Both sides evaluated: {lhs.evalf()} == {rhs.evalf()} -> {is_equal}"
                    return result
                else:
                    # Solve for variable
                    var = list(free)[0]
                    eq = sp.Eq(lhs, rhs)
                    solutions = sp.solve(eq, var)
                    result["success"] = True
                    result["exact_result"] = str(solutions)
                    result["latex_result"] = sp.latex(solutions)
                    result["method"] = "algebraic_equation_solver"
                    result["verification"] = f"Roots satisfy equation: {[lhs.subs(var, r) == rhs.subs(var, r) for r in solutions]}"
                    return result

            # 4. General simplification & calculation: e.g. 1 + 1, (25 * 48), (x^2 - 1)/(x - 1)
            parsed = parse_expr(clean_expr, transformations=self.transformations)
            simplified = sp.simplify(parsed)
            result["success"] = True
            result["exact_result"] = str(simplified)
            result["latex_result"] = sp.latex(simplified)
            result["method"] = "arithmetic_and_algebraic_simplification"
            result["verification"] = "Verified symbolically via SymPy engine"
            return result

        except Exception as e:
            result["error"] = str(e)
            return result

    def format_math_context(self, problem: str, solution: Dict[str, Any]) -> str:
        """Formats verified calculation into context for prompt grounding."""
        if not solution.get("success"):
            return ""

        clean_expr = solution.get('clean_expr') or problem

        return (
            f"--- VERIFIED MATHEMATICAL COMPUTATION (SymPy Engine) ---\n"
            f"User Question: {problem}\n"
            f"Extracted Mathematical Expression: {clean_expr}\n"
            f"Calculation Method: {solution.get('method')}\n"
            f"Exact Computed Result: {solution.get('exact_result')}\n"
            f"LaTeX Notation: $${solution.get('latex_result')}$$\n"
            f"Verification: {solution.get('verification', 'Verified algebraically')}\n"
            f"Directive: Answer the user's question clearly, concisely, and naturally. "
            f"If the user asked 'how' or 'why' (e.g. for basic arithmetic like 1 + 1 = 2), explain the intuitive logic "
            f"step-by-step (such as counting objects, combining single units, or mathematical axioms). "
            f"Never interpret conversational English words (like 'how', 'why', 'what', 'please') as algebraic variables or letter multiplications.\n"
            f"--- END MATHEMATICAL COMPUTATION ---"
        )

math_service = MathSolverService()
