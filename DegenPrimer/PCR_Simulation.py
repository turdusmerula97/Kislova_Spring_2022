#!/usr/bin/python
# coding=utf-8
#
# Copyright (C) 2012 Allis Tauri <allista@gmail.com>
# 
# degen_primer is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# indicator_gddccontrol is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
Created on Nov 16, 2012

@author: Allis Tauri <allista@gmail.com>
'''

from copy import deepcopy
from datetime import timedelta
from math import log, exp
from Equilibrium import Equilibrium
import StringTools
import TD_Functions
from TD_Functions import format_PCR_conditions
from StringTools import wrap_text, line_by_line, hr



class Region(object):
    '''Region of a sequence.'''
    def __init__(self, name, start, end):
        self.name  = name
        if start < 1 or end < 1:
            raise ValueError('Region: start and end of a sequence region should be grater than 1.')
        if start > end:
            raise ValueError('Region: start of a sequence region should be less than it\'s end')
        self.start  = start
        self.end    = end
    #end def

    def pretty_print(self, with_name=True):
        rep  = ''
        if with_name:
            rep += 'target: %s\n' % self.name
        rep += 'start:  %d\n' % self.start
        rep += 'end:    %d\n' % self.end
        rep += 'length: %d\n' % len(self)
        return rep
    #end def
    
    def __str__(self): return self.pretty_print()
    
    def __len__(self): return self.end - self.start +1
        
    def __hash__(self): return hash((self.name, self.start, self.end))
    
    def __eq__(self, other):
        return self.__hash__() == other.__hash__()
    
    def __ne__(self, other):
        return self.__hash__() != other.__hash__()
        
    def __iadd__(self, T):
        if self.name != T.name: return self
        self.start = min(self.start, T.start)
        self.end   = max(self.end, T.end)
        return self
    #end def
    
    def overlaps(self, T):
        return (self.name == T.name 
                and
                (self.start <= T.start <= self.end)
                or
                (self.start <= T.end <= self.end))
    #end def
#end class


class Product(Region):
    '''Representation of a PCR product. A product is defined as a sequence 
    region bounded by start and end positions which correspond to 3' ends of 
    primers (forward and reverse) which produce this product.'''
    def __init__(self, template_name, start, end, 
                 fwd_primers=None, rev_primers=None):
        Region.__init__(self, template_name, start, end)
        #quantity and number of cycles
        self._quantity    = 0
        self._cycles      = 0
        #primers and templates
        self._fwd_ids     = set()
        self._rev_ids     = set()
        self.fwd_primers  = set()
        self.rev_primers  = set()
        self._fwd_margin  = self.start-1
        self._rev_margin  = self.end+1
        if self._fwd_margin < 1: self._fwd_margin = 1
        self.fwd_template = Region(template_name, self._fwd_margin, self._fwd_margin)
        self.rev_template = Region(template_name, self._rev_margin, self._rev_margin)
        for primer in fwd_primers:
            self.add_fwd_primer(primer)
        for primer in rev_primers:
            self.add_rev_primer(primer)
    #end def
    
    
    def pretty_print(self, with_name=True):
        rep  = Region.pretty_print(self, with_name=with_name)
        rep += '\n'
        rep += 'concentration:    %s\n' % TD_Functions.format_concentration(self._quantity)
        rep += 'number of cycles: %d\n' % self.cycles
        rep += '\n'
        rep += hr(' forward annealing site ')
        rep += self.fwd_template.pretty_print(with_name=False)
        rep += '\n'
        rep += hr(' reverse annealing site ')
        rep += self.rev_template.pretty_print(with_name=False)
        rep += '\n'
        rep += hr(' forward primers ')
        fwd_primers = list(self.fwd_primers)
        fwd_primers.sort(key=lambda x: x[1])
        for primer, _id in fwd_primers:
            rep += _id + ':\n' + repr(primer) + '\n'
        rep += '\n'
        rep += hr(' reverse primers ')
        rev_primers = list(self.rev_primers)
        rev_primers.sort(key=lambda x: x[1])
        for primer, _id in rev_primers:
            rep += _id + ':\n' + repr(primer) + '\n'
        return rep
    #end def
    
    
    def __str__(self):
        rep  = Region.pretty_print(self)
        rep += 'concentration:    %s\n' % TD_Functions.format_concentration(self._quantity)
        rep += 'number of cycles: %d\n' % self.cycles
        rep += '\nforward annealing site:\n'
        rep += str(self.fwd_template)
        rep += '\nreverse annealing site:\n'
        rep += str(self.rev_template)
        rep += '\nforward primers:\n'
        fwd_primers = list(self.fwd_primers)
        fwd_primers.sort(key=lambda x: x[1])
        for primer, _id in fwd_primers:
            rep += _id + ':\n' + repr(primer) + '\n'
        rep += '\nreverse primers:\n'
        rev_primers = list(self.rev_primers)
        rev_primers.sort(key=lambda x: x[1])
        for primer, _id in rev_primers:
            rep += _id + ':\n' + repr(primer) + '\n'
        return rep
    #end def
    
    
    def __iadd__(self, T):
        if self.name != T.name: return self
        if self.start > T.start:
            self.start        = T.start
            self._fwd_margin  = T._fwd_margin
            self.fwd_template = deepcopy(T.fwd_template)
            self.fwd_primers  = deepcopy(T.fwd_primers)
        elif self.start == T.start:
            for _primer in T.fwd_primers:
                self.add_fwd_primer(_primer)
        if self.end < T.end:
            self.end          = T.end
            self._rev_margin  = T._rev_margin
            self.rev_template = deepcopy(T.rev_template)
            self.rev_primers  = deepcopy(T.rev_primers)
        elif self.end == T.end:
            for _primer in T.rev_primers:
                self.add_rev_primer(_primer)
        return self
    #end def
    
    
    @property
    def quantity(self): return self._quantity
    
    @quantity.setter
    def quantity(self, q): self._quantity = q
        
    @property
    def fwd_ids(self):
        _ids = [primer[1] for primer in self.fwd_primers]
        _ids.sort() 
        return _ids
    
    @property
    def rev_ids(self): 
        _ids = [primer[1] for primer in self.rev_primers]
        _ids.sort() 
        return _ids

    def add_fwd_primer(self, primer):
        if primer in self.fwd_primers: return
        self.fwd_primers.add(primer)
        self.fwd_template += Region(self.name, 
                                    max(self.start-primer[0].fwd_len, 1), 
                                    max(self.start-1, 1))
    #end def
        
    def add_rev_primer(self, primer):
        if primer in self.rev_primers: return
        self.rev_primers.add(primer)
        self.rev_template += Region(self.name, 
                                    self.end+1, 
                                    self.end+primer[0].fwd_len)
    #end def
#end class
    


class PCR_Simulation(object):
    '''In silica PCR results filtration, computation and visualization.'''
    
    #histogram
    _all_products_title  = 'PCR-product'
    _hist_column_title   = '     final concentration     '
    #bar width should not be less than 2*len('100.00%')+1, or value will not fit
    _hist_width          = max(2*len('999.9 mM')+2, len(_hist_column_title)) 
    #electrophoresis
    _window_percent      = 0.05 #percentage of a length of the longest PCR product; it defines band width on electrophoresis
    #indirectly defines to what extent should lengths 
    #of two products differ in order of them to occupy 
    #separate bands on the electrophoresis.
    _precision           = 1e6
    #minimum equilibrium constant: reactions with EC less than this will not be taken into account
    _min_K               = 100
    #products with quantity less than maximum quantity multiplied by this factor will not be included in the report
    _min_quantity_factor = 0.001


    def __init__(self, 
                 primers,                #all primers (generally degenerate) that may be present in the system
                 min_amplicon,           #minimum amplicon length 
                 max_amplicon,           #maximum amplicon length
                 polymerase,             #polymerase concentration in Units per liter
                 with_exonuclease=False, #if polymerase does have have 3' exonuclease activity, products of primers with 3'-mismatches will also be icluded
                 num_cycles=20,          #number of PCR cycles
                 ):
        self._primers             = primers
        self._min_amplicon        = min_amplicon
        self._max_amplicon        = max_amplicon
        self._polymerase          = polymerase
        self._with_exonuclease    = with_exonuclease
        self._elongation_time     = max_amplicon/1000.0 #minutes
        self._num_cycles          = num_cycles
        self._reaction_ends       = dict()

        self._nonzero   = False  #true if there're some products and their quantities were calculated
        
        self._templates = dict() #list of all templates
        self._products  = dict() #dictionary of all possible products
        self._side_reactions = dict() #dictionary of all reactions
        self._side_concentrations   = dict()
        self._primer_concentrations = dict()
        for primer in self._primers:
            self._primer_concentrations.update(dict.fromkeys(primer.str_sequences, 
                                                             primer.concentration))
        
        self._solutions = dict() #solutions of equilibrium systems
        self._max_objective_value = -1 #objective value of the worst solution
    #end def
    
    
    def __nonzero__(self):
        return self._nonzero

    def hits(self):
        return list(self._products.keys())
    
    def add_side_concentrations(self, concentrations):
        if concentrations: self._side_concentrations.update(concentrations)
        
    def add_side_reactions(self, reactions):
        if not reactions: return 
        self._side_reactions.update(dict([R for R in reactions.items() 
                                          if R[1]['constant'] >= self._min_K
                                          or R[1]['type'] == 'A']))
    #end def
        

    def add_product(self, 
                    hit,          #name of the target sequence
                    start,        #start position of the product on the target sequence
                    end,          #end position of the product on the target sequence
                    fwd_duplexes, #duplexes of forward primers with corresponding template sequence
                    rev_duplexes, #duplexes of reverse primers with corresponding template sequence
                    ):
        '''
        Add a new product to the simulation.
        hit -- name of template sequence (termed as in BLAST)
        start, end -- positions in the sequence (starting form 1) corresponding 
        to the beginning and the end of PCR prduct
        *_duplexes -- lists of tuples of the form (duplex_object, id), where 
        duplex_object represents annealed primer and id is it's name 
        '''
        #check amplicon length
        if not (self._min_amplicon <= end-start+1 <= self._max_amplicon): 
            return False
        #check fwd primers
        valid_fwd = []
        for fwd_duplex, _id in fwd_duplexes:
            #check equilibrium constant
            if fwd_duplex.K < self._min_K: continue
            #check 3' mismatches
            if not self._with_exonuclease and fwd_duplex.fwd_3_mismatch:
                continue
            #check if there are such primers in the system at all
            for primer in self._primers:
                if fwd_duplex.fwd_seq in primer:
                    valid_fwd.append((fwd_duplex, _id))
                    break
        #check rev primers
        valid_rev = []
        for rev_duplex, _id in rev_duplexes:
            #check equilibrium constant
            if rev_duplex.K < self._min_K: continue
            #check 3' mismatches
            if not self._with_exonuclease and rev_duplex.fwd_3_mismatch:
                continue
            #check if there are such primers in the system at all
            for primer in self._primers:
                if rev_duplex.fwd_seq in primer:
                    valid_rev.append((rev_duplex, _id))
                    break
        #if there are no valid fwd and rev primers, return
        if not valid_fwd or not valid_rev: return False
        #initialize new product and reset nonzero flag
        new_product = Product(hit, start, end, valid_fwd, valid_rev)
        self._nonzero = False
        #if there was no such hit before, add it
        if hit not in self._products:
            self._products[hit] = dict()
        #if no such product from this hit, add it to the list
        new_product_hash = hash(new_product)
        if new_product_hash not in self._products[hit]:
            self._products[hit][new_product_hash]  = new_product
        else: #append primers
            self._products[hit][new_product_hash] += new_product
        #add templates
        self._add_template(hit, self._products[hit][new_product_hash].fwd_template)
        self._add_template(hit, self._products[hit][new_product_hash].rev_template)
        return True
    #end def
    
    
    def _add_alternative_annealing(self, duplex, _id, max_3_matches):
        '''Add alternative annealig of a primer to a template as a side reaction'''
        pass
    #end def
    
    
    def _add_template(self, hit, new_template):
        #add new template
        if hit not in self._templates:
            self._templates[hit] = []
        self._templates[hit].append(new_template)
        self._templates[hit].sort(key=lambda(x): x.start)
        compacted = [self._templates[hit][0]]
        for T in self._templates[hit]:
            if T.overlaps(compacted[-1]):
                compacted[-1] += T
            else: compacted.append(T)
        self._templates[hit] = compacted
    #end def
    
    
    def _find_template(self, hit, query_template):
        for T in self._templates[hit]:
            if T.overlaps(query_template):
                return T
        return None
    
    
    def _construct_reactions(self, hit_ids):
        reactions = dict()
        for hit_id in hit_ids:
            for product in self._products[hit_id].values():
                fwd_template = self._find_template(hit_id, product.fwd_template)
                for fwd_primer, _id in product.fwd_primers:
                    r_hash = hash((fwd_primer.fwd_seq, fwd_template))
                    reactions[r_hash] = Equilibrium.compose_reaction(fwd_primer.K, 
                                                                     fwd_primer.fwd_seq, 
                                                                     hash(fwd_template), 'AB')
                rev_template = self._find_template(hit_id, product.rev_template)
                for rev_primer, _id in product.rev_primers:
                    r_hash = hash((rev_primer.fwd_seq, rev_template))
                    reactions[r_hash] = Equilibrium.compose_reaction(rev_primer.K, 
                                                                     rev_primer.fwd_seq, 
                                                                     hash(rev_template), 'AB')
        return reactions
    #end def
    
            
    def _calculate_equilibrium(self):
        #compose a list of reactant concentrations
        self._max_objective_value = 0
        for hit_id in self._products.keys():
            #assemble reactions and concentrations for this hit
            reactions = self._construct_reactions((hit_id,))
            if not reactions:
                self._solutions[hit_id] = None
                continue
            reactions.update(self._side_reactions)
            concentrations = dict(self._primer_concentrations)
            concentrations.update([(hash(T), TD_Functions.C_DNA) 
                                   for T in self._templates[hit_id]])
            concentrations.update(self._side_concentrations)
            #calculate equilibrium
            equilibrium = Equilibrium(reactions, concentrations)
            equilibrium.calculate()
            self._solutions[hit_id]   = equilibrium
            self._max_objective_value = max(self._max_objective_value, 
                                            equilibrium.solution_objective_value)
    #end def
    
    
    def run(self):
        if not self._products: return
        #calculate equilibrium in the system
        self._calculate_equilibrium()
        #compute quantities of products, filter out those with low quantity
        for hit_id in self._products:
            equilibrium = self._solutions[hit_id]
            if not equilibrium:
                self._products[hit_id] = dict() 
                continue
            solution   = equilibrium.solution
            cur_state  = [TD_Functions.C_dNTP*4.0, #a matrix is considered to have equal quantities of each letter
                          dict(self._primer_concentrations), []]
            self._reaction_ends[hit_id] = {'poly':[],
                                           'cycles':3}
            cur_primers,cur_variants = cur_state[1],cur_state[2]
            for product_id in self._products[hit_id]:
                product = self._products[hit_id][product_id]
                #forward primer annealing, first cycle
                fwd_strands_1 = dict()
                fwd_template  = self._find_template(hit_id, product.fwd_template)
                for fwd_primer, _id in product.fwd_primers:
                    r_hash = hash((fwd_primer.fwd_seq, fwd_template))
                    if r_hash in solution:
                        fwd_strands_1[fwd_primer.fwd_seq] = [solution[r_hash],
                                                             equilibrium.get_product_concentration(r_hash)]
                        cur_primers[fwd_primer.fwd_seq] -= fwd_strands_1[fwd_primer.fwd_seq][1] 
                        cur_state[0] -= fwd_strands_1[fwd_primer.fwd_seq][1]*len(product)
                #reverse primer annealing, first cycle
                rev_strands_1 = dict()
                rev_template  = self._find_template(hit_id, product.rev_template)
                for rev_primer, _id in product.rev_primers:
                    r_hash = hash((rev_primer.fwd_seq, rev_template))
                    if r_hash in solution:
                        rev_strands_1[rev_primer.fwd_seq] = [solution[r_hash],
                                                             equilibrium.get_product_concentration(r_hash)]
                        cur_primers[rev_primer.fwd_seq] -= rev_strands_1[rev_primer.fwd_seq][1]
                        cur_state[0] -= rev_strands_1[rev_primer.fwd_seq][1]*len(product)
                #second and third cycles
                for f_id in fwd_strands_1:
                    for r_id in rev_strands_1:
                        #second
                        fwd_strand_2  = (fwd_strands_1[f_id][0])*(rev_strands_1[r_id][1])
                        rev_strand_2  = (rev_strands_1[r_id][0])*(fwd_strands_1[f_id][1])
                        cur_primers[f_id] -= fwd_strand_2
                        cur_primers[r_id] -= rev_strand_2
                        cur_state[0] -= (fwd_strand_2+rev_strand_2)*len(product)
                        #third
                        var = [f_id, r_id, fwd_strand_2+rev_strand_2, product_id]
                        cur_variants.append(var)
                        cur_primers[f_id] -= rev_strand_2
                        cur_primers[r_id] -= fwd_strand_2
                        cur_state[0] -= (fwd_strand_2+rev_strand_2)*len(product)
            if not cur_variants:
                self._products[hit_id] = dict() 
                continue
            #check if primers or dNTP were used in the first three cycles
            if cur_state[0] <= 0 or min(cur_state[1]) <= 0:
                print '\nPCR simulation warning:'
                print '   Template DNA: %s' % hit_id
                if cur_state[0] <= 0:
                    print '   dNTP have been depleted in the first three cycles.'
                if min(cur_state[1]) <= 0:
                    print '   Some primers have been depleted in the first three cycles.'
                print 'Try to change reaction conditions.'
                self._products[hit_id] = dict()
                continue
            #all consequent PCR cycles
            cur_variants.sort(key=lambda(x): x[2])
            for cycle in range(4, self._num_cycles+1):
                idle = True
                #save current state
                prev_state = deepcopy(cur_state)
                #calculate a normal cycle
                for var in cur_variants:
                    #if any primer is depleted, continue
                    if cur_primers[var[0]] is None \
                    or cur_primers[var[1]] is None: 
                        continue
                    #count consumption
                    cur_primers[var[0]] -= var[2]
                    cur_primers[var[1]] -= var[2]
                    cur_state[0] -= var[2]*2*len(self._products[hit_id][var[3]])
                    #count synthesis
                    var[2] += var[2]
                    #something was synthesized in this cycle
                    idle = False
                if idle: break #all primers have been depleted
                self._correct_cycle(hit_id, cycle, prev_state, cur_state)
                #count the cycle of each synthesized products
                for var0, var1 in zip(prev_state[2], cur_state[2]):
                    if var0[2] != var1[2]: 
                        self._products[hit_id][var1[3]].cycles = cycle
                #count the cycle of the reaction
                self._reaction_ends[hit_id]['cycles'] = cycle
                #if no dNTP left, end the reaction
                if cur_state[0] <= 0: break
            #end cycles
            self._reaction_ends[hit_id]['dNTP'] = cur_state[0]/4.0 if cur_state[0] >= 0 else 0
            #sum up all variants of each product
            for var in cur_variants:
                self._products[hit_id][var[3]].quantity += var[2]
            #filter out products with zero quantity
            max_product_quantity   = max(prod[1].quantity 
                                         for prod in self._products[hit_id].items())
            self._products[hit_id] = dict([prod for prod in self._products[hit_id].items() 
                                          if prod[1].quantity > max(TD_Functions.C_DNA, 
                                                                    max_product_quantity*self._min_quantity_factor)])
        #filter out hits without proucts
        self._products = dict([hit for hit in self._products.items() 
                               if len(hit[1]) > 0])
        self._nonzero  = len(self._products) > 0
    #end def


    def _correct_cycle(self, hit_id, cycle, prev_state, cur_state):
        prev_dNTP,prev_primers,prev_variants = prev_state
        cur_dNTP,cur_primers,cur_variants = cur_state
        #check if: some primers were depleted
        depleted_primers = dict()
        for p_id in cur_primers:
            if  cur_primers[p_id] != None \
            and cur_primers[p_id] < 0:
                consume_ratio = (prev_primers[p_id]/
                                 (prev_primers[p_id] 
                                  - cur_primers[p_id]))
                depleted_primers[p_id] = consume_ratio
        #if so, recalculate consumption for products which use them
        if depleted_primers:
            for var0, var1 in zip(prev_variants, cur_variants):
                if  not var1[0] in  depleted_primers \
                and not var1[1] in  depleted_primers:
                    continue
                if cur_primers[var1[0]] is None \
                or cur_primers[var1[1]] is None: 
                    continue
                consume_ratio0 = depleted_primers[var1[0]] if var1[0] in depleted_primers else 1
                consume_ratio1 = depleted_primers[var1[1]] if var1[1] in depleted_primers else 1
                real_addition = (var1[2]-var0[2])*min(consume_ratio0,
                                                      consume_ratio1)
                #restore subtracted
                cur_primers[var1[0]] += var0[2]
                cur_primers[var1[1]] += var0[2]
                cur_dNTP += var0[2]*2*len(self._products[hit_id][var1[3]])
                #subtract real consumption
                cur_primers[var1[0]] -= real_addition
                cur_primers[var1[1]] -= real_addition
                cur_dNTP -= real_addition*2*len(self._products[hit_id][var1[3]])
                #count synthesis
                var1[2] = var0[2] + real_addition
        #set depleted primers to exact zero (due to floating point errors they may still be small real numbers)
        for p_id in depleted_primers: cur_primers[p_id] = 0
        #check if: dNTP was used,
        #     and  polymerase activity could handle this cycle.                    
        dNTP_consumption = prev_dNTP - cur_dNTP
        max_consumptioin = self._polymerase*10e-9*self._elongation_time/30
        #save polymerase shortage information
        if dNTP_consumption > max_consumptioin:
            if self._reaction_ends[hit_id]['poly']:
                #if previous cycle passed without a shortage, start new record
                if cycle - self._reaction_ends[hit_id]['poly'][-1][1] > 1:
                    self._reaction_ends[hit_id]['poly'].append([cycle, cycle])
                else: #append to the current record 
                    self._reaction_ends[hit_id]['poly'][-1][1] = cycle
            else: #if there was no shortage, add current new record
                self._reaction_ends[hit_id]['poly'].append([cycle, cycle])
        #correct consumption if needed
        if dNTP_consumption > max_consumptioin \
        or cur_dNTP < 0:
            consume_ratio = min(max_consumptioin/dNTP_consumption,
                                prev_dNTP/dNTP_consumption)
            cur_dNTP = prev_dNTP
            cur_primers.update(prev_primers)
            for var0, var1 in zip(prev_variants, cur_variants):
                if cur_primers[var1[0]] is None \
                or cur_primers[var1[1]] is None: 
                    continue
                #due to primer correction var1[2]-var0[2] is not always equal to var0[2]
                real_addition = (var1[2]-var0[2])*consume_ratio
                cur_primers[var1[0]] -= real_addition  
                cur_primers[var1[1]] -= real_addition
                cur_dNTP -= real_addition*2*len(self._products[hit_id][var1[3]])
                var1[2] = var0[2] + real_addition
        cur_state[0] = cur_dNTP
        #check again if some primers were depleted
        for p_id in cur_primers:
            if cur_primers[p_id] <= 0:
                cur_primers[p_id] = None
    #end def
    
    
    @classmethod
    def _construct_histogram(cls, main_title, products, reaction_ends=None, with_titles=True, sort=True):
        #construct histogram
        histogram  = []
        max_start  = max(len(str(p.start)) for p in products)
        max_end    = max(len(str(p.end))   for p in products)
        max_len    = max(len(str(len(p)))  for p in products)
        for product in products:
            product_spec = ''
            #if the flag is set, print full hit title
            if with_titles:
                product_spec += product.name + '\n'
            #compose product specification
            product_spec  += '%d%s bp [%d%s-%s%d]' \
                           % (len(product),
                              ' '*(max_len-len(str(len(product)))),
                              product.start,
                              ' '*(max_start-len(str(product.start))),
                              ' '*(max_end-len(str(product.end))),
                              product.end)
            #print last cycle of the reaction where this product was still generating
            if reaction_ends:
                product_spec += ' %d cycles' % product.cycles
            product_spec += '\n'
            #print primers which give this product
            if not with_titles:
                primer_ids  = ', '.join(product.fwd_ids)
                if primer_ids: primer_ids += ' <> '
                primer_ids += ', '.join(product.rev_ids)
                if primer_ids: product_spec += primer_ids + '\n'
            #append histogram row
            histogram.append([product_spec, product.quantity, len(product)])
        #sort histogram by product length, from the longest to the shortest
        if sort: histogram.sort(key=lambda(x): x[2], reverse=True)
        #format histogram
        return cls._format_histogram(main_title, histogram)
    #end def
    
    
    @classmethod
    def _format_histogram(cls, title, histogram):
        #maximum column name width and value
        max_value = max(c[1] for c in histogram)
        widths    = [StringTools.text_width-cls._hist_width-1, cls._hist_width+1]
        histogram_string  = '-'*StringTools.text_width + '\n'
        #wrap column and hist titles
        histogram_string += line_by_line([title, cls._hist_column_title], 
                                         widths, j_center=True)
        histogram_string += '-'*StringTools.text_width + '\n'
        #histogram lines
        for col in histogram:
            #line value
            hist_value = int(round((cls._hist_width*col[1])/max_value))
            col_spacer = cls._hist_width - hist_value
            #value figure
            value_str  = TD_Functions.format_concentration(col[1])
            hist_bar  = ''
            if len(value_str) < col_spacer:
                _spacer = col_spacer-len(value_str)
                hist_bar += '#'*hist_value + ' '*_spacer + value_str 
            else:
                _bar = hist_value-len(value_str)
                hist_bar += '#'*(_bar/2) + value_str 
                hist_bar += '#'*(_bar-_bar/2) + ' '*col_spacer
            histogram_string += line_by_line([col[0],hist_bar], widths, divider=':')
            histogram_string += '-'*StringTools.text_width + '\n'
        histogram_string += '\n'
        return histogram_string
    #end def
    
    
    def _construct_electrophoresis(self, products):
        max_len      = max(len(p) for p in products)
        window       = int(max_len*self._window_percent)
        nearest_srip = max_len-window
        max_len_log  = int(log(max_len)*self._precision)
        min_len_log  = int(log(min(len(p) for p in products))*self._precision)
        window_log   = int((log(max_len)-log(nearest_srip))*self._precision)
        #construct phoresis
        phoresis    = [[l,0,int(exp(l/self._precision))] for l in range(min_len_log, max_len_log+window_log, window_log)]
        for product in products:
            l = int(log(len(product))*self._precision)
            p = (l - min_len_log)/window_log
            #fluorescence intensity is proportional to the length of a duplex
            phoresis[p][1] += product.quantity*len(product)
        phoresis = phoresis[::-1]
        #format electrophorogram
        return self._format_electrophoresis(window, phoresis)
    #end def
    
    
    def _format_electrophoresis(self, window, phoresis):
        text_width  = StringTools.text_width
        max_line    = max(min(p.concentration for p in self._primers)*self._max_amplicon, 
                          max(l[1] for l in phoresis))
        max_mark    = max(len(str(l[2]+window)) for l in phoresis)*2
        line_width  = text_width - max_mark - 7 #mark b :###   :
        #format phoresis
        phoresis_text = ''
        phoresis_text += ' '*(max_mark+5)+':'+'-'*line_width+':\n'
        phoresis_text += ' '*(max_mark+5)+':'+' '*line_width+':\n'
        for l in range(len(phoresis)):
            line = phoresis[l]
            prev_mark   = phoresis[l-1][2] if l > 0 else line[2]+window
            mark_spacer = max_mark - len(str(line[2])) - len(str(prev_mark))
            line_value  = int(round((line_width*line[1])/max_line))
            line_spacer = line_width - line_value 
            phoresis_text += '%d-%d%s bp :%s%s:\n' % (prev_mark,
                                                      line[2], 
                                                      ' '*mark_spacer,
                                                      '#'*line_value,
                                                      ' '*line_spacer) 
        phoresis_text += ' '*(max_mark+5)+':'+' '*line_width+':\n'
        phoresis_text += ' '*(max_mark+5)+':'+'-'*line_width+':\n'
        return phoresis_text
    #end def
    

    def per_hit_header(self, hit):
        if not self._nonzero: 
            return '\nNo PCR products have been found.\n'
        header_string  = ''
        header_string += 'Reaction ended in: %d cycles.\n' \
            % self._reaction_ends[hit]['cycles']
        header_string += 'C(dNTP) after reaction: ~%s\n' \
            % TD_Functions.format_concentration(self._reaction_ends[hit]['dNTP'])
        if self._reaction_ends[hit]['cycles'] < self._num_cycles:
            if self._reaction_ends[hit]['dNTP'] == 0:
                header_string += 'dNTP have been depleted.\n'
            else:
                header_string += 'Primers have been depleted.\n'
        if self._reaction_ends[hit]['poly']:
            header_string += wrap_text('Polymerase activity was '
                                       'insufficient in these cycles:\n')
            shortage_string = ''
            for shortage_period in self._reaction_ends[hit]['poly']:
                if shortage_string: shortage_string += ', '
                if shortage_period[0] == shortage_period[1]:
                    shortage_string += str(shortage_period[0])
                else:
                    shortage_string += '%d-%d' % tuple(shortage_period)
            header_string += wrap_text(shortage_string + '\n')
        header_string += '\n'
        return header_string

        
    def all_products_histogram(self):
        if not self._nonzero: 
            return '\nNo PCR products have been found.\n'
        all_products = []
        prods_list = self._products.values()
        prods_list.sort(key=lambda(d): max(p.quantity for p in d.values()), reverse=True)
        for p_dict in prods_list:
            prods = p_dict.values()
            prods.sort(key=len, reverse=True)
            all_products += prods
        return self._construct_histogram(self._all_products_title, all_products, 
                                         None, with_titles=True, sort=False)
    #end def
    
    
    def per_hit_histogram(self, hit):
        if not self._nonzero: 
            return '\nNo PCR products have been found.\n'
        products = self._products[hit].values()
        return self._construct_histogram('%s' % hit, products, 
                                         self._reaction_ends, with_titles=False)
    #end def
    
    
    def per_hit_electrophoresis(self, hit):
        if not self._nonzero: 
            return '\nNo PCR products have been found.\n'
        products = self._products[hit].values()
        return self._construct_electrophoresis(products)
    #end def
    
    
    def all_graphs_grouped_by_hit(self):
        if not self._nonzero: 
            return '\nNo PCR products have been found.\n'
        all_graphs = ''
        prods = self._products.items()
        prods.sort(key=lambda(d): max(p.quantity for p in d[1].values()), reverse=True)
        hits = [p[0] for p in prods]
        for hit in hits:
            all_graphs += self.per_hit_histogram(hit)
            all_graphs += self.per_hit_header(hit)
            all_graphs += hr(' electrophorogram of PCR products ')
            all_graphs += self.per_hit_electrophoresis(hit)
            all_graphs += hr('')
            all_graphs += '\n\n'
        return all_graphs
    
    
    def format_report_header(self):
        header_string  = ''
        header_string += hr(' PCR conditions ')
        if self._with_exonuclease:
            header_string += "DNA polymerase HAS 3'-5'-exonuclease activity.\n"
        else: header_string += "DNA polymerase doesn't have 3'-5'-exonuclease activity.\n"
        header_string += 'Speed of DNA polymerase is considered to be 1 kbs/min\n\n'
        header_string += 'Minimum amplicon size: %d\n' % self._min_amplicon
        header_string += 'Maximum amplicon size: %d\n' % self._max_amplicon
        header_string += 'Elongation time:       %s\n' % timedelta(minutes=self._elongation_time)
        header_string += 'Maximum cycles:        %d\n' % self._num_cycles
        header_string += '\n'
        header_string += format_PCR_conditions(self._primers, self._polymerase)+'\n'
        header_string += hr(' primers and their melting temperatures ')
        for primer in self._primers:
            header_string += repr(primer) + '\n'
        header_string += '\n'
        return header_string
    #end def
    
    
    def format_quantity_explanation(self):
        expl_string  = ''
        expl_string += hr(' estimation of PCR products concentrations ')
        expl_string += 'Value of an objective function at the solution ' + \
                       '(the lower the better):\n   %e\n' % \
                        self._max_objective_value
        expl_string += wrap_text('This value shows "distance" to the solution of '
                           'the system of equilibrium equations which were used '
                           'to calculate concentrations of PCR products.\n\n')
        expl_string += wrap_text(('Products with concentration less than %.2f%% '
                                  'of the concentration of the most abundant '
                                  'product or less than initial DNA concentration '
                                  'are not shown.'
                                 '\n\n') % (self._min_quantity_factor*100))
        expl_string += wrap_text('Boundaries of a product and it\'s length do '
                                 'not include primers.\n\n')
        expl_string += '\n'
        return expl_string
    #end def
    
    
    def format_products_report(self):
        prod_string  = ''
        prod_string += wrap_text('For each target sequence a list of possible '
                                 'PCR products which were predicted by the '
                                 'simulation is given. ' 
                                 'Information about each product includes:\n'
                                 '-start and end positions on a target sequence.\n'
                                 '   *the first nucleotide of a sequence is at the position 1\n'
                                 '   *primers are not included, so their 3\'-ends are located at '
                                 'start-1 and end+1 positions.\n'
                                 '-length in base pairs.\n'
                                 '   *the length too do not include primers.\n'
                                 '-concentration which was calculated during PCR simulation.\n'
                                 '-number of PCR cycles during which the product has been generated.\n'
                                 '   *if this number is lower than the number of simulated reaction cycles '
                                 'it means that primers producing the product were depleted.\n'
                                 '-lists of forward and reverse primers which produced the product'
                                 '\n\n\n')
        for hit in self._products:
            prod_string += hr(' %s ' % hit, '*')
            products = self._products[hit].values()
            products.sort(key=lambda x: x.start)
            for pi, product in enumerate(products):
                prod_string += hr(' product %d ' % (pi+1), '=')
                prod_string += product.pretty_print(with_name=False)
                prod_string += hr('', '=')
            prod_string += hr('', '*')
        prod_string += '\n'
        return prod_string
#end class



#test
if __name__ == '__main__':
    import StringTools
    from SecStructures import Duplex
    from Primer import Primer
    import os
    os.chdir('../')
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.Alphabet import IUPAC
    TD_Functions.C_dNTP = 0.02e-3
    TD_Functions.C_DNA  = 1e-10
    TD_Functions.PCR_T  = 60
    primers = []
    primers.append(Primer.from_sequences((SeqRecord(Seq('ATATTCTACGACGGCTATCC', IUPAC.unambiguous_dna), id='F-primer'),
                                          SeqRecord(Seq('ATATGCTACGACGGCTATCC', IUPAC.unambiguous_dna)),
                                          SeqRecord(Seq('ATATTCTACGACGGCTATCC', IUPAC.unambiguous_dna))), 
                                         0.1e-6))
    primers.append(Primer.from_sequences((SeqRecord(Seq('CAAGGGCTAGAAGCGGAAG'[::-1], IUPAC.unambiguous_dna), id='R-primer'),
                                          SeqRecord(Seq('CAAGGGCTAGACGCGGAAG'[::-1], IUPAC.unambiguous_dna)),
                                          SeqRecord(Seq('CAAGGCCTAGAGGCGGAAG'[::-1], IUPAC.unambiguous_dna))),
                                         0.1e-6))
    PCR_res = PCR_Simulation(primers, 500, 3000, 0.01*1e6, False, 30)
    PCR_res.add_product('Pyrococcus yayanosii CH1', 982243, 983644,
                        Duplex(Seq('ATATTCTACGACGGCTATCC'), 
                               Seq('ATATTCTACGACGGCTATCC').reverse_complement()),
                        Duplex(Seq('CAAGGGCTAGAAGCGGAAG'[::-1]), 
                               Seq('CAAGGGCTAGAAGCGGAAG').complement())) 
    PCR_res.add_product('Pyrococcus yayanosii CH1', 962243, 963744,
                        Duplex(Seq('ATATTCTACGACGGCTATCC'), 
                               Seq('ATATTCTACGACGGCTATCC').reverse_complement()),
                        Duplex(Seq('CAAGGGCTAGAAGCGGAAG'[::-1]), 
                               Seq('CAAGGGCTAGAAGCGGAAG').complement()))
    PCR_res.add_product('Pyrococcus yayanosii CH2', 962243, 963644, 
                        Duplex(Seq('ATATGCTACGACGGCTATCC'), 
                               Seq('ATATGCTACGACGGCTATCC').reverse_complement()),
                        Duplex(Seq('CAAGGGCTAGACGCGGAAG'[::-1]), 
                               Seq('CAAGGGCTAGACGCGGAAG').complement()))
    PCR_res.add_product('Pyrococcus yayanosii CH3', 922243, 923644, 
                        Duplex(Seq('ATATTCTACGACGGCTATCC'), 
                               Seq('ATATTCTACGACGGCTATCC').reverse_complement()),
                        Duplex(Seq('CAAGGCCTAGAGGCGGAAG'[::-1]), 
                               Seq('CAAGGCCTAGAGGCGGAAG').complement()))

    PCR_res.run()
    print PCR_res.format_report_header()
    print PCR_res.format_quantity_explanation()
    print PCR_res.all_products_histogram()
    print ''
    print PCR_res.all_graphs_grouped_by_hit()
