""" 
This file will contain the function to compute the Groebner basis 
of the invariant ring using the algorithm 2.1.10 presented in 
Gatermann's paper
"""

from funcs.func_utils import *
from funcs.hilbert import *
from funcs.groebner2 import *
import sympy as sy
import numpy as np

from itertools import combinations_with_replacement, combinations

def mn_comb(m,n):
    """
    Generates all possible combinations of m numbers that sums up to n
    """
    combs = []
    for c in combinations_with_replacement(range(n+1), m):
        if sum(c) == n:
            combs.append(c)
    return combs

def M_subs(poly, x_symbols, expressions):
    """
    Function to replace y_i in poly as list of monomials expressions
    Inputs:
    poly: sympy expression of a polynomial
    x_symbols: original variables for the expressionn
    expressions: monomials that is substituted into polynomial
    """
    temp = sy.symbols('t:{}'.format(len(x_symbols)))
    subs_poly = poly.as_expr()
    for term, t in zip(x_symbols, temp):
        subs_poly = subs_poly.subs(term, t)
    for t, mon in zip(temp, expressions):
        subs_poly = subs_poly.subs(t, mon)
    subs_poly = sy.expand(subs_poly)
    return subs_poly

def polynomial_to_matrix(mons, polys):
    mat = sy.zeros(len(polys), len(mons))
    for i, poly in enumerate(polys):
        for j, mon in enumerate(mons):
            c, mon = mon.as_coeff_Mul()
            coeff = poly.coeff(mon)
            mat[i,j] = coeff
    return mat

def row_echeon_ind(mat):
    """
    Assuming row echelon matrix, get the indices of the non-zero rows
    """
    non_zero_rows = []
    for i in range(mat.shape[0]):
        if mat[i, :].norm() != 0:
            non_zero_rows.append(i)
    return non_zero_rows

def tup_mon(tup, syms):
    """
    Converts the power tupe into a monomial given symbols
    """
    expression = 1.0
    for i in range(len(tup)):
        expression *= syms[i]**tup[i]
    return expression

def reynold(poly, G, syms):
    """
    Computes the Reynold projection of polynomial under actions of finite group G
    
    Inputs:
    poly: sympy expression 
    G: finite group with matrix representation
    syms: sympy variables for poly
    """
    rey = 0
    # Compute the replaced expressions
    for g in G:
        expressions = tuple(g * sy.Matrix(syms))
        rey += M_subs(poly, syms, expressions)
    return (1/len(G))*rey

def inv_ring(G, mol, t, x, W, d):
    """
    Implementation of algorithm 2.1.10 for finite groups

    Inputs:
    G: A finite group under matrix representation, a list of Sympy matrices
    mol: Molien series of the finite group G
    t: sympy symbol (variable) for Molien series
    x: sympy symbols (variables) of the polynomial ring K[x]
    W: Weight system that induces a term order (which can be extended to an elimination order), Sympy matrix
    d: Maximal degree to compute invariants up to
    """
    # Initialisation
    eli_W = W # Elimination order extended from term order defined by 
    invs = [] # set of invariants
    m = 0 # no. of invariants found (constant is always invariant)
    GB = [] # Groebner basis for the invariant ring
    HT = [] # set of leading terms of GB - poly expressions
    mol = hilb_expand(mol, t, d) 
    l = sy.symbols('l:{}'.format(W.shape[0]))
    HP = sy.poly(1,t) # Initialise the tentative Hilbert series for ideal generated by invariants
    mol_hp_diff = mol - HP
    k_list = mod_merge_sort(list(mol_hp_diff.as_dict().keys()))[::-1]
    k = k_list.pop() # Minimum degree of missing invariants - power tuple
    N = sy.Matrix([tuple([1]*len(x))]) # Natural grading for x symbols
    while k[0] <= d[0]:
        y = sy.symbols('y_:{}'.format(m))
        s = int(mol_hp_diff.as_dict()[k]) # no. of invariants at degree k
        V = mn_comb(len(x), k[0]) # This is a list of tuples
        V += [tuple(reversed(c)) for c in V if c[0] != c[1]]
        all_V = [tup_mon(v,x) for v in V]
        inv_degs = [weighted_deg(N,leading_term(N,inv,y)) for inv in invs]
        ind_W = sy.Matrix(list(inv_degs))
        all_y_comb = list(combinations_with_replacement(range(k[0]+1), len(y)))
        y_comb = [c for c in all_y_comb if weighted_deg(ind_W, c) == k[0]] # This is a list of tuples
        M = [tup_mon(c, y) for c in y_comb]
        M = [M_subs(m ,y, HT) for m in M]
        V = [mon for mon in all_V if mon not in M]
        Q = [reynold(mon, G, x) for mon in V]
        Q = list(set([q for q in Q if q != 0]))
        Q_mat = polynomial_to_matrix(all_V, Q)
        Q_mat, rows = Q_mat.rref()
        Q_ind = row_echeon_ind(Q_mat)
        Q = [Q[i] for i in Q_ind]
        P = []
        for i in range(len(Q)):
            h = normalf(eli_W, GB, sy.poly(Q[i],x+y), x+y)
            # Check if h contains x_i variables
            if bool(h.free_symbols.intersection(x)):
                x_sub = [0.]*len(x)
                p = Q[i] - M_subs(h, x+y, x_sub + invs)
                p = normalf(W, P, sy.poly(p, x), x)
                if not p.is_zero:
                    P.append(sy.poly(p,x))
        invs.extend(P)
        mol_hp_diff = mol - HP
        # Extend the y symbols to extended invariants
        y += (tuple([sy.symbols('y_%d' % i) for i in range(m, m+s)]))
        eli_W = sy.Matrix([tuple(eli_W) + tuple([1]*s)])
        # Extend the induced weight order to extended invariants
        inv_degs = [weighted_deg(N,leading_term(N,inv,y))[0] for inv in invs]
        ind_W = sy.Matrix([inv_degs])
        GB.extend([y[m+i] - P[i] for i in range(s)])
        GB = [sy.poly(poly, x+y) for poly in GB]
        GB, message = dtrunc_groebner(eli_W, eli_W.shape[0], eli_W, k, GB, mol.as_expr(), x+y, l, dom=None)
        # Extend the leading terms of GB that is only dependent on y_i
        to_ext = [f for f in GB if not bool(f.free_symbols.intersection(x))]
        HT = [leading_term(eli_W, sy.poly(poly,x+y), x+y) for poly in to_ext]
        # Change dimensions of leading term tuples to be compatible for x_i
        HT = [ht[:len(x)] for ht in HT]
        hp, l = hilbert(HT, ind_W, y)
        HP = hilb_expand(hp, l, d)
        HP = sy.poly(HP, l)
        m += s
        mol_hp_diff = mol - HP
        if mol_hp_diff.is_zero:
            return invs
        k_list = list(sy.poly(mol_hp_diff, t).as_dict().keys())
        k_list = mod_merge_sort(k_list)[::-1]
        k = k_list.pop()
        if k[0] > d[0]:
            return invs
    return invs




        
