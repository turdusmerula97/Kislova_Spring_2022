# Copyright (C) 2012 Allis Tauri <allista@gmail.com>
# 
# degen_primer is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# degen_primer is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
Created on Jan 1, 2013

@author: Allis Tauri <allista@gmail.com>
'''

import numpy as np
from array import array
from scipy.fftpack import fft, ifft
from SecStructures import Duplex
from StringTools import print_exception
from MultiprocessingBase import MultiprocessingBase

class SearchEngine(MultiprocessingBase):
    '''Fast search of a pattern sequence in a given set of template sequences 
    with parallelization using multiprocessing.'''
    
    _w_3_0 = 1                        #trivial 3d root of unity 
    _w_3_1 = (-1/2.0+np.sqrt(3)/2.0j) #3d root of unity in a power of 1
    _w_3_2 = (-1/2.0-np.sqrt(3)/2.0j) #3d root of unity in a power of 2
    
    _unambiguous = array('b','ATGC')  #ATGC characters as byte array
    
    #alphabet mappings to the 3d roots of unity for templates and patterns
    _T_AT_mapping = dict(zip(_unambiguous, (_w_3_1,_w_3_2,0,0))) 
    
    _T_GC_mapping = dict(zip(_unambiguous, (0,0,_w_3_1,_w_3_2)))

    _P_AT_mapping = {'A':_w_3_2,
                     'T':_w_3_1,
                     'G':_w_3_0,
                     'C':_w_3_0,
                     
                     'R':_w_3_2,
                     'Y':_w_3_1,
                     'S':_w_3_0,
                     'W':_w_3_2+_w_3_1,
                     'K':_w_3_1,
                     'M':_w_3_2,
                     'B':_w_3_1,
                     'D':_w_3_2+_w_3_1,
                     'H':_w_3_2+_w_3_1,
                     'V':_w_3_2,
                     'N':_w_3_2+_w_3_1}
    
    _P_GC_mapping = {'A':_w_3_0,
                     'T':_w_3_0,
                     'G':_w_3_2,
                     'C':_w_3_1,
                     
                     'R':_w_3_2,
                     'Y':_w_3_1,
                     'S':_w_3_2+_w_3_1,
                     'W':_w_3_0,
                     'K':_w_3_2,
                     'M':_w_3_1,
                     'B':_w_3_2+_w_3_1,
                     'D':_w_3_2,
                     'H':_w_3_1,
                     'V':_w_3_2+_w_3_1,
                     'N':_w_3_2+_w_3_1}
    
    #template sequences grater than this value will be split into slices of 
    #approximately that size 
    _max_chunk_size = 2**12
    ###########################################################################


    @classmethod
    def set_max_chunk(cls, chunk_size):
        cls._max_chunk_size = chunk_size
    

    @staticmethod
    def _map_letter(letter, _map):
        try: return _map[letter]
        except KeyError: return 0
    #end def
    
    
    @classmethod
    def _map_pattern(cls, pattern, map_len):
        '''Map pattern sequence to an alphabet of 3d roots of unity.'''
        #this naive algorithm works ~5 times faster 
        #than the one used for template mapping due to short length of patterns
        AT_map = np.zeros(map_len, dtype=complex)
        GC_map = np.zeros(map_len, dtype=complex)
        for i,letter in enumerate(pattern):
            AT_map[i] = cls._map_letter(letter, cls._P_AT_mapping)
            GC_map[i] = cls._map_letter(letter, cls._P_GC_mapping)
        return (AT_map, GC_map)
    #end def
    

    @staticmethod
    def _compile_duplexes_for_position(position, template, primer, 
                                           t_len, p_len, reverse):
        '''Given a template strand, a primer and a location where the 
        primer matches the template, return a list of Duplexes formed by 
        unambiguous components of the primer'''
        duplexes = []
        for var in primer.seq_records:
            dup = Duplex(var.seq, template[position:position+p_len].complement()[::-1])
            if not dup: continue
            duplexes.append((dup, var.id))
        if not reverse:
            return position+p_len, duplexes
        else:
            return t_len+1-(position+p_len), duplexes
    #end def
    _compile_duplexes_mapper = staticmethod(MultiprocessingBase._data_mapper(_compile_duplexes_for_position.__func__)) 
    
    
    @staticmethod
    @MultiprocessingBase._results_assembler
    def _duplexes_assembler(index, result, output):
        if result[1]: output.append(result)
    #end def
    

    def _compile_duplexes_mp(self, 
                               fwd_seq, rev_seq, primer, 
                               t_len, p_len,
                               fwd_matches, rev_matches):
        '''Compile duplexes for both strands of a template in parallel'''
        #prepare and start two sets of jobs
        fwd_jobs = self._prepare_jobs(self._compile_duplexes_mapper, 
                                      fwd_matches, self.cpu_count, 
                                      fwd_seq, primer, t_len, p_len, False)
        rev_jobs = self._prepare_jobs(self._compile_duplexes_mapper, 
                                      rev_matches, self.cpu_count,
                                      rev_seq, primer, t_len, p_len, True)
        self._start_jobs(fwd_jobs+rev_jobs)
        #allocate containers for results
        fwd_results = []
        rev_results = []
        #assemble results
        self._join_jobs(fwd_jobs, 1, 
                        self._duplexes_assembler, fwd_results)
        self._join_jobs(rev_jobs, 1, 
                        self._duplexes_assembler, rev_results)
        #if aborted, return None
        if self._abort_event.is_set(): return None
        #else, cleanup
        self._clean_jobs(fwd_jobs+rev_jobs)
        #sort duplexes by position and return them
        fwd_results.sort(key=lambda x: x[0])
        rev_results.sort(key=lambda x: x[0])
        return fwd_results,rev_results
    #end def
    
    
    def _compile_duplexes(self, 
                            fwd_seq, rev_seq, primer, 
                            t_len, p_len,
                            fwd_matches, rev_matches):
        '''Compile duplexes for both strands of a template'''
        fwd_results = []
        for pos in fwd_matches:
            if self._abort_event.is_set(): break
            duplexes = self._compile_duplexes_for_position(pos, fwd_seq, primer, 
                                                           t_len, p_len, reverse=False)
            if duplexes[1]: fwd_results.append(duplexes)
        rev_results = []
        for pos in rev_matches:
            if self._abort_event.is_set(): break
            duplexes = self._compile_duplexes_for_position(pos, rev_seq, primer, 
                                                           t_len, p_len, reverse=True)
            if duplexes[1]: rev_results.append(duplexes)
        #if aborted, return None
        if self._abort_event.is_set(): return None
        return fwd_results,rev_results
    #end def
        
    
    @classmethod
    def _find_in_chunk(cls, t_chunk, p_fft, correction, c_size, c_stride):
        '''Find number of matches of pattern at each position in a given 
        chunk of a template.
        Pattern is given as a polynomial evaluated at n-th roots of unity 
        using fft.
        map_len is a length of a map of template to the alphabet of 3-d roots 
        of unity chunk to build. It's a power of 2 integer for fft to work fast.
        c_stride -- a part of chunk for which matches are calculated 
        (it is less than map_len, so chunks overlap each other)'''
        t_AT_map = np.fromiter(array('b',str(t_chunk)), dtype=complex) 
        t_AT_map.resize(c_size)
        t_GC_map = t_AT_map.copy()
        for k,v in cls._T_AT_mapping.iteritems():
            t_AT_map[t_AT_map == k] = v
        for k,v in cls._T_GC_mapping.iteritems():
            t_GC_map[t_GC_map == k] = v
        AT_score = ifft(fft(t_AT_map[::-1])*p_fft[0])[::-1][:c_stride]
        GC_score = ifft(fft(t_GC_map[::-1])*p_fft[1])[::-1][:c_stride]
        score    = AT_score.real + GC_score.real
        score    = (score + correction - score/3.0)
        return score
    #end def
    
    
    @classmethod
    def _calculate_chunk_size(cls, t_len, p_len):
        rem = lambda(c): ((t_len/(c-p_len))*(c-p_len)+c-t_len)
        if t_len <= cls._max_chunk_size:
            chunk = 2**int(np.ceil(np.log2(t_len)))
            if chunk % t_len == 0: return chunk
        else: chunk = cls._max_chunk_size
        r = rem(chunk)
        min_chunk = 2**int(np.ceil(np.log2(2*p_len)))
        max_rem   = chunk/2+1
        while r > max_rem \
        and chunk > min_chunk:
            chunk /= 2
            r = rem(chunk)
        return max(chunk, min_chunk)
    #end def
    
    
    @staticmethod
    def _check_length_inequality(t_len, p_len):
        if t_len < p_len or p_len == 0:
            raise ValueError('SearchEngine._find: template sequence should be '
                             'longer or equal to primer sequence and both '
                             'should be grater than zero.')

    
    @classmethod
    def mp_better(cls, t_len):
        #based on computation time statistics
        return cls.cpu_count > 1 and t_len > 25000
    
    
    @classmethod
    def _optimal_slices(cls, t_len, p_len):
        #linear regression of measured computing time with respect to 
        #number of slices and template length
        linear = max(cls.cpu_count, int(t_len*1.75e-5 + 1.75)) 
        return min(60, linear, t_len/p_len)
    #end def
    
    
    def _start_find_worker(self, jobs, queue, start, fwd_seq, rev_seq, 
                             p_fft, correction, end, s_stride, c_size, c_stride):
        @MultiprocessingBase._worker
        def worker(abort_e, start, fwd_seq, rev_seq, p_fft, 
                   correction, end, s_stride, c_size, c_stride):
            fwd_score = np.ndarray(0,dtype=float)
            rev_score = np.ndarray(0,dtype=float)
            pos = start
            while pos < end and not abort_e.is_set():
                front = min(end, pos+c_size)
                score = self._find_in_chunk(fwd_seq[pos:front], p_fft, correction,
                                            c_size, c_stride)
                fwd_score = np.concatenate([fwd_score, score])
                score = self._find_in_chunk(rev_seq[pos:front], p_fft, correction,
                                            c_size, c_stride)
                rev_score = np.concatenate([rev_score, score])
                pos += c_stride
            return (start, 
                    fwd_score[:s_stride], 
                    rev_score[:s_stride])
        #end def
        job = self._Process(target=worker, 
                            args=(queue, self._abort_event, start, fwd_seq, rev_seq, p_fft, 
                                  correction, end, s_stride, c_size, c_stride))
        job.daemon = 1
        job.start()
        jobs.append((job,queue))
    #end def
    

    def _find_mp(self, template, primer, t_len, p_len, mismatches):
        '''Find all occurrences of a primer sequence in both strands of a 
        template sequence with at most k mismatches. Multiprocessing version.'''
        slice_size   = t_len/self._optimal_slices(t_len, p_len)+p_len+1
        slice_stride = slice_size-p_len
        chunk_size   = self._calculate_chunk_size(slice_size, p_len)
        chunk_stride = chunk_size-p_len
        p_maps       = self._map_pattern(str(primer.master_sequence.seq), chunk_size)
        p_fft        = (fft(p_maps[0]),fft(p_maps[1]))
        fwd_seq      = template.seq
        rev_seq      = template.seq.reverse_complement()
        correction   = np.ndarray(chunk_stride); correction.fill(p_len/3.0)
        fwd_score    = []
        rev_score    = []
        jobs         = []
        #start find_in_chunk jobs
        i = 0 
        while i < t_len and not self._abort_event.is_set():
            front = min(t_len, i+slice_size)
            self._start_find_worker(jobs, self._Queue(), i, 
                                    fwd_seq, rev_seq, p_fft, 
                                    correction, front, slice_stride, chunk_size, chunk_stride)
            self._register_job(jobs[-1])
            i += slice_stride
        #join all jobs
        def parse_out(out, fwd_list, rev_list):
            fwd_list.append((out[0],out[1]))
            rev_list.append((out[0],out[2]))
        self._join_jobs(jobs, 1, parse_out, fwd_score, rev_score)
        #if search was aborted, return empty results
        if self._abort_event.is_set(): return None
        #else, cleanup
        self._clean_jobs(jobs)
        #sort, correct and concatenate scores
        fwd_score.sort(key=lambda(x): x[0])
        fwd_score = [result[1] for result in fwd_score]
        rev_score.sort(key=lambda(x): x[0])
        rev_score = [result[1] for result in rev_score]
        fwd_score = np.concatenate(fwd_score)[:t_len]
        rev_score = np.concatenate(rev_score)[:t_len]
        #match indices
        matches     = max(1, p_len - mismatches)-0.5
        fwd_matches = np.arange(t_len-p_len+1)[fwd_score[:t_len-p_len+1] >= matches]; del fwd_score
        rev_matches = np.arange(t_len-p_len+1)[rev_score[:t_len-p_len+1] >= matches]; del rev_score
        #construct and return duplexes
        return self._compile_duplexes_mp(fwd_seq, rev_seq, primer, 
                                         t_len, p_len, fwd_matches, rev_matches)
    #end def

    
    def _find(self, template, primer, t_len, p_len, mismatches):
        '''Find all occurrences of a primer sequence in both strands of a 
        template sequence with at most k mismatches.'''
        chunk_size   = self._calculate_chunk_size(t_len, p_len)
        chunk_stride = chunk_size-p_len
        p_maps       = self._map_pattern(str(primer.master_sequence.seq), chunk_size)
        p_fft        = (fft(p_maps[0]),fft(p_maps[1]))
        fwd_seq      = template.seq
        rev_seq      = template.seq.reverse_complement()
        fwd_score    = []
        rev_score    = []
        correction   = np.ndarray(chunk_stride); correction.fill(p_len/3.0)
        #_find in chunks of a template, which is faster due to lower cost of memory allocation
        i = 0
        while i < t_len and not self._abort_event.is_set():
            front = min(t_len, i+chunk_size)
            fwd_score.append(self._find_in_chunk(fwd_seq[i:front], p_fft, correction, 
                                                 chunk_size, chunk_stride))
            
            rev_score.append(self._find_in_chunk(rev_seq[i:front], p_fft, correction, 
                                                 chunk_size, chunk_stride))
            i += chunk_stride
        #if search was aborted, return empty results
        if self._abort_event.is_set(): return None
        #concatenate scores
        fwd_score = np.concatenate(fwd_score)
        rev_score = np.concatenate(rev_score)
        #match indices
        matches     = max(1, p_len - mismatches)-0.5
        fwd_matches = np.arange(t_len-p_len+1)[fwd_score[:t_len-p_len+1] >= matches]; del fwd_score
        rev_matches = np.arange(t_len-p_len+1)[rev_score[:t_len-p_len+1] >= matches]; del rev_score
        #construct and return duplexes
        return self._compile_duplexes(fwd_seq, rev_seq, primer, 
                                      t_len, p_len, fwd_matches, rev_matches)
    #end def
    
    
    def find(self, template, primer, mismatches):
        '''Find occurrences of a degenerate primer in a template sequence.
        Return positions and Duplexes formed. This method uses 
        multiprocessing to speedup the search process. Use it to perform 
        search in a long sequence.''' 
        p_len,t_len = len(primer),len(template)
        self._check_length_inequality(t_len, p_len)
        results = None
        if self.mp_better(t_len):
            results = self._find_mp(template, primer, t_len, p_len, mismatches)
        else:
            results = self._find(template, primer, t_len, p_len, mismatches)
        return results
    #end def
    
    
    @MultiprocessingBase._data_mapper_method
    def _batch_find(self, template, primer, p_len, mismatches):
        t_id, t_len, _template = template
        result = self._find(_template, primer, t_len, p_len, mismatches)
        return t_id, result
    #end def
    
    
    def batch_find(self, templates, primer, mismatches):
        '''Find occurrences of a degenerate primer in each of the provided 
        templates. Return dictionary of results using template IDs as keys.
        It uses multiprocessing to parallelize searches, each of which does 
        not use parallelization. Use it to search in many short sequences.'''
        p_len   = len(primer)
        jobs    = self._prepare_jobs(self._batch_find, templates, 
                                     None,
                                     primer, p_len, mismatches)
        self._start_jobs(jobs)
        results = dict()
        self._join_jobs(jobs, 1, self._ordered_results_assembler, results)
        if self._abort_event.is_set(): return None
        return results
    #end def
#end class



if __name__ == '__main__':
    #tests
    import signal
    import cProfile
    import gc
    from time import time
    import sys, os, csv, timeit
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.Alphabet import IUPAC
    from Primer import Primer
    from multiprocessing import Event
    
    searcher = None
    ppid     = -1
    data1    = []
    data2    = []
    abort_event = Event()
    
    def sig_handler(signal, frame):
        if ppid != os.getpid():
            return
        print 'Aborting main process %d' % os.getpid()
        abort_event.set()
        if data1:
            print 'Write out gathered data1...'
            out_file = open('gather_data1-%d.csv' % time(), 'wb')
            csv_writer = csv.writer(out_file, delimiter='\t', quotechar='"')
            csv_writer.writerows(data1)
            out_file.close()
            print 'Done.'
        if data2:
            print 'Write out gathered data2...'
            out_file = open('gather_data2-%d.csv' % time(), 'wb')
            csv_writer = csv.writer(out_file, delimiter='\t', quotechar='"')
            csv_writer.writerows(data2)
            out_file.close()
            print 'Done.'
        sys.exit(1)
    #end def

    #setup signal handler
    signal.signal(signal.SIGINT,  sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGQUIT, sig_handler)

    os.chdir('../')
    seq_file = 'ThGa.fa'
    try:
        record_file = open(seq_file, 'r')
    except IOError, e:
        print 'Unable to open %s' % seq_file
        print_exception(e)
        sys.exit(1)
    record = SeqIO.read(record_file, 'fasta', IUPAC.unambiguous_dna)
    record_file.close()
    
    query = Seq('ATATTCTACRACGGCTATCC', IUPAC.ambiguous_dna)
    query = Seq('GACTAATGCTAACGGGGGATT', IUPAC.ambiguous_dna)
    query = Seq('AGGGTTAGAAGNACTCAAGGAAA', IUPAC.ambiguous_dna)
    
    ftgam_f = Seq('ATATTCTACRACGGCTATCC', IUPAC.ambiguous_dna)
    
    template = record#+record+record+record
#    query    = query+query+query+query+query

    searcher = SearchEngine(abort_event)
    primer   = Primer(SeqRecord(ftgam_f, id='ftgam_f'), 0.43e-6)
    primer.generate_components()

    def print_out(out, name):
        print name
        for i, results in enumerate(out):
            if not results: 
                print 'No results.'
            else:
                print 'Results %d' % i
                for res in results:
                    print res[0]
                    for dup, _id in res[1]:
                        print _id
                        print dup
                        #print 'mismatches:', dup.mismatches
                    print '\n'
                print '\n'
    #end def
    
    
    def gather_statistics1(start_len, end_len, delta, title=None):
        global ppid, data1, data2, T,P,mult
        ppid  = os.getpid()
        p_len = 20
        lens  = range(start_len, end_len+1, delta)
        if title:
            data2 = [('t_len', 'p_len', '_find time %s'%title, 
                      '_find_mp time %s'%title)]
        else: data2 = [('t_len', 'p_len', '_find time', '_find_mp time')]
        find_times    = dict([(l,[]) for l in lens])
        find_mp_times = dict([(l,[]) for l in lens])
        for i in xrange(20):
            print 'iteration', i
            for t_len in lens:
                print 't_len:',t_len
                T = template[:t_len]
                P = Primer(SeqRecord(query[:p_len], id='test'), 0.1e-6)
                et = timeit.timeit('searcher._find(T, P, 3)', 
                                   setup='from __main__ import T,P,searcher', 
                                   number=1)
                find_times[t_len].append(et)
                et = timeit.timeit('searcher._find_mp(T, P, 3)', 
                                   setup='from __main__ import T,P,searcher', 
                                   number=1)
                find_mp_times[t_len].append(et)
                print ''
        for t_len in lens:
            data2.append((t_len, p_len, 
                          min(find_times[t_len]), min(find_mp_times[t_len])))
        if title:
            filename = 'find_mp_vs_find-%s-%d.csv' % (title, time())
        else: filename = 'find_mp_vs_find-%d.csv' % time()
        out_file = open(filename, 'wb')
        csv_writer = csv.writer(out_file, delimiter='\t', quotechar='"')
        csv_writer.writerows(data2)
        out_file.close()
        data2 = []
        print 'Gather statistics 1: data was written to %s' % filename 
    #end def

    ppid = os.getpid()
    
#    from multiprocessing.managers import BaseManager
#    class MyManager(BaseManager): pass
#    MyManager.register('SearchEngine', SearchEngine)
#    mgr = MyManager(); mgr.start()
#    del searcher
#    searcher = mgr.SearchEngine()
    
    import TD_Functions
    TD_Functions.PCR_P.PCR_T = 48
    
#    from tests.asizeof import mem_used
#    t0 = time()
#    results = searcher.find(template, primer, 9)
#    mem_used(results)
#    t1 = (time()-t0)
#    print_out(results, 'test')
#    print 'elapsed %f seconds\n' % t1 

#    t0 = time()
#    templates = [(1,23885,template[:23885]),
#                 (2,23435,template[:23435]),
#                 (3,23835,template[:23835]),
#                 (4,2432,template[:2432]),
#                 (5,538827,template[:538827])]
#    results = searcher.batch_find(templates, Primer(SeqRecord(query[:23], id='test'), 0.1e-6), 7)
#    for rid in results:
#        print '\n'
#        print_out(results[rid], rid)
#    print 'elapsed %f seconds\n' % (time()-t0)
#    gather_statistics1(5000, 500000, 5000)
    
#    for l in [2**10, 2**11, 2**12, 2**13, 2**14, 2**15, 2**16]:
#        searcher.set_max_chunk(l)
#        gather_statistics1(205000, 400000, 5000, str(l))
        
#    while True:
#        gather_statistics(50000, 500000, 50000)
#        gather_statistics(600000, 1000000, 100000)
#        gather_statistics(1100000, 1500000, 100000)
#        gather_statistics(1600000, 2000000, 100000)
#        gather_statistics(1800000, 2600000, 200000)
#        gather_statistics(2800000, 4000000, 400000)
        #gather_statistics(5000000, 10000000, 1000000)
        
    
#    cProfile.run('''
#for i in xrange(10): 
#    searcher.find(template, primer, 9)
#    ''', 
#    'Dimer_new-find.profile')

    t_len = len(template)
    p_len = len(primer)
    cProfile.run('''
for i in xrange(10): 
    searcher._find(template, primer, t_len, p_len, 6)
    ''', 
    'Dimer_new-find.profile')
    
#    from scipy.stats import sem
#    find_times = [timeit.timeit('searcher.find(template, primer, 9)', 'from __main__ import template, primer, searcher', number=1) for _i in xrange(10)]
#    print 'mean time: %.02f\nsem: %.02f' % (np.mean(find_times), sem(find_times))
    


#    ar1, ar2 = None,None
#    for l in [2**10, 2**11, 2**12, 2**13, 2**14, 2**15, 2**16]:
#        ar1 = np.random.random_sample(l).astype(complex)
#        ar2 = np.random.random_sample(l).astype(complex)
#        times = []
#        for i in xrange(10):
#            et = timeit.timeit('ifft(fft(ar1)*fft(ar2))', 
#                               setup='from __main__ import ar1, ar2\n'
#                                     'from scipy.fftpack import fft, ifft', 
#                               number=10)
#            times.append(et)
#        print '%d %f' % (l, min(times))
#        cProfile.run("for i in xrange(10):\
#            ifft(fft(ar1)*fft(ar2))",
#            'ifft_fft_%d.profile'%l)
    
    
    #print_out(out0, '_find')
    #print_out(out1, '_find_mp')
    print 'Done'
