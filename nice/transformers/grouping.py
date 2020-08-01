import numpy as np
from nice.unrolling_individual_pca import UnrollingIndividualPCA
#from cython.parallel cimport prange
from nice.transformers.compressors import IndividualLambdaPCAsBoth
from nice.thresholding import get_thresholded_tasks
from nice.nice_utilities import do_partial_expansion, Data, get_sizes
from nice.ClebschGordan import ClebschGordan, check_clebsch_gordan
from nice.packing import unite_parallel, subtract_parallel, pack_dense, unpack_dense
from parse import parse
import warnings
from sklearn.linear_model import Ridge
from sklearn.base import clone
from sklearn.exceptions import NotFittedError       
        
       
def check_if_all_fitted(parts):
    all_fitted = True
    for part in parts:
        if (part is not None):
            all_fitted = all_fitted and part.is_fitted()
    return all_fitted

class InitialTransformer():
    def __init__(self):
        self.fitted_ = True
    def transform(self, coefficients):
        l_max = coefficients.shape[2] - 1
        even_coefficients = np.copy(coefficients)
        even_coefficients_sizes = [coefficients.shape[1] if i % 2 == 0 else 0 for i in range(l_max + 1)]

        odd_coefficients = np.copy(coefficients)
        odd_coefficients_sizes = [coefficients.shape[1] if i % 2 == 1 else 0 for i in range(l_max + 1)]
        
        return Data(even_coefficients, even_coefficients_sizes), Data(odd_coefficients, odd_coefficients_sizes)
    
class StandardBlock():    
        
    def __init__(self, covariants_expansioner = None, covariants_purifier = None, covariants_pca = None, invariants_expansioner = None, invariants_purifier = None, invariants_pca = None, guaranteed_parts_fitted_consistently = False):
        
        self.covariants_expansioner_ = covariants_expansioner
        if (self.covariants_expansioner_ is not None):
            if self.covariants_expansioner_.mode_ != 'covariants':
                raise ValueError("mode of covariants expansioner should be covariants")  
        
        self.covariants_purifier_ = covariants_purifier
        if (self.covariants_purifier_ is not None) and (self.covariants_expansioner_ is None):
            raise ValueError("can not purify covariants without covariants")
            
        
        self.covariants_pca_ = covariants_pca
        if (self.covariants_pca_ is not None) and (self.covariants_expansioner_ is None):
            raise ValueError("can not do pca over not existing covariants")
        
        self.invariants_expansioner_ = invariants_expansioner
        if (self.invariants_expansioner_ is not None):
            if self.invariants_expansioner_.mode_ != 'invariants':
                raise ValueError("mode of invariants expansioner should be invariants")
        
        self.invariants_purifier_ = invariants_purifier
        if (self.invariants_purifier_ is not None) and (self.invariants_expansioner_ is None):
            raise ValueError("can not purify invariants without invariants")
            
        self.invariants_pca_ = invariants_pca
        if (self.invariants_pca_ is not None) and (self.invariants_expansioner_ is None):
            raise ValueError("can not do pca over not existing invariants")
            
        if (self.covariants_expansioner_ is not None) and (self.covariants_pca_ is not None):
            self.higher_body_orders_possible_ = True
        else:
            self.higher_body_orders_possible_ = False
            
        if (self.covariants_expansioner_ is None) and (self.invariants_expansioner_ is None):
            raise ValueError("nothing to do")
            
        self.fitted_ = guaranteed_parts_fitted_consistently and check_if_all_fitted([covariants_expansioner, covariants_purifier, covariants_pca, invariants_expansioner, invariants_purifier, invariants_pca])
        
    def fit(self, first_even, first_odd, second_even, second_odd, 
            old_even_covariants = None, old_odd_covariants = None,
            old_even_invariants = None, clebsch_gordan = None):
        
        
        self.l_max_ = first_even.covariants_.shape[2] - 1
        if clebsch_gordan is None:
            self.clebsch_ = ClebschGordan(self.l_max_)
        else:
            check_clebsch_gordan(clebsch_gordan, self.l_max_)
            self.clebsch_ = clebsch_gordan
        
        
        if (self.covariants_expansioner_ is not None):
            self.covariants_expansioner_.fit(first_even, first_odd, second_even, second_odd, clebsch_gordan = self.clebsch_)
            transformed_even, transformed_odd = self.covariants_expansioner_.transform(first_even, first_odd, second_even, second_odd)
            
        if (self.covariants_purifier_ is not None):
            
            if (old_even_covariants is None) or (old_odd_covariants is None):
                raise ValueError("to fit covariants purifier previous covariants should be provided")
            
            self.covariants_purifier_.fit(old_even_covariants, transformed_even, old_odd_covariants, transformed_odd)
            transformed_even, transformed_odd = self.covariants_purifier_.transform(old_even_covariants, transformed_even, old_odd_covariants, transformed_odd)
        
                
                
        if (self.covariants_pca_ is not None):
            self.covariants_pca_.fit(transformed_even, transformed_odd)
            
        if (self.invariants_expansioner_ is not None):
            self.invariants_expansioner_.fit(first_even, first_odd, second_even, second_odd, clebsch_gordan = self.clebsch_)
            invariants_even, _ = self.invariants_expansioner_.transform(first_even, first_odd, second_even, second_odd)
            
        if (self.invariants_purifier_ is not None):
            if (old_even_invariants is None):
                raise ValueError("to fit invariants purifier previous invariants should be provided")
            self.invariants_purifier_.fit(old_even_invariants, invariants_even)
            invariants_even = self.invariants_purifier_.transform(old_even_invariants, invariants_even)
            
        if (self.invariants_pca_ is not None):            
            self.invariants_pca_.fit(invariants_even)
            
        self.fitted_ = True
        
    def transform(self, first_even, first_odd, second_even, second_odd, old_even_covariants = None, old_odd_covariants = None,
            old_even_invariants = None):
        if (not self.fitted_):
            raise NotFittedError("instance of {} is not fitted. It can not transform anything".format(type(self).__name__))
        transformed_even, transformed_odd = None, None
        if (self.covariants_expansioner_ is not None):
            transformed_even, transformed_odd = self.covariants_expansioner_.transform(first_even, first_odd, second_even, second_odd)
            
        if (self.covariants_purifier_ is not None):
            if (old_even_covariants is None) or (old_odd_covariants is None):
                raise ValueError("need previous covariants to do covariants purifier transformation")
            transformed_even, transformed_odd = self.covariants_purifier_.transform(old_even_covariants, transformed_even, old_odd_covariants, transformed_odd)
            
        if (self.covariants_pca_ is not None):
            transformed_even, transformed_odd = self.covariants_pca_.transform(transformed_even, transformed_odd)
        
        invariants_even = None
        if (self.invariants_expansioner_ is not None):
            invariants_even, _ = self.invariants_expansioner_.transform(first_even, first_odd, second_even, second_odd)
        if (self.invariants_purifier_ is not None):
            if (old_even_invariants is None):
                raise ValueError("need previous invariants to do invariants purifier transformation")
            invariants_even = self.invariants_purifier_.transform(old_even_invariants, invariants_even)
            
        if (self.invariants_pca_ is not None):
            invariants_even = self.invariants_pca_.transform(invariants_even)
       
        return transformed_even, transformed_odd, invariants_even
    
    def is_fitted(self):
        return self.fitted_
        
    
class StandardSequence():
    def __init__(self, blocks, initial_pca = IndividualLambdaPCAsBoth(), guaranteed_parts_fitted_consistently = False):
        self.blocks_ = blocks
        self.initial_pca_ = initial_pca
        for i in range(len(self.blocks_) - 1):
            if not self.blocks_[i].higher_body_orders_possible_:
                raise ValueError("all intermediate standard blocks should calculate covariants")
        self.initial_transformer_ = InitialTransformer()
        self.fitted_ = guaranteed_parts_fitted_consistently and check_if_all_fitted(blocks + [self.initial_pca_, self.initial_transformer_])       
   
    def fit(self, coefficients, clebsch_gordan = None):
        
        self.l_max_ = coefficients.shape[2] - 1
        if clebsch_gordan is None:
            self.clebsch_ = ClebschGordan(self.l_max_)
        else:
            check_clebsch_gordan(clebsch_gordan, self.l_max_)
            self.clebsch_ = clebsch_gordan
            
        self.intermediate_sizes_ = []
        data_even_0, data_odd_0 = self.initial_transformer_.transform(coefficients)
        self.initial_pca_.fit(data_even_0, data_odd_0)
        data_even_0, data_odd_0 = self.initial_pca_.transform(data_even_0, data_odd_0)
        
        data_even_now, data_odd_now = data_even_0, data_odd_0
        all_invariants = [data_even_0.get_invariants()]
        all_even_covariants = [data_even_0]
        all_odd_covariants = [data_odd_0]
        
        self.intermediate_sizes_.append([data_even_now.actual_sizes_, data_odd_now.actual_sizes_])
        for i in range(len(self.blocks_)):
            self.blocks_[i].fit(data_even_now, data_odd_now, data_even_0, data_odd_0, all_even_covariants, all_odd_covariants, all_invariants, clebsch_gordan = self.clebsch_)            
            data_even_now, data_odd_now, invariants_even_now = self.blocks_[i].transform(data_even_now, data_odd_now, data_even_0, data_odd_0, all_even_covariants, all_odd_covariants, all_invariants)
            
            all_even_covariants.append(data_even_now)
            all_odd_covariants.append(data_odd_now)
            
            if (invariants_even_now is not None):
                all_invariants.append(invariants_even_now)
            else:
                all_invariants.append(data_even_now.get_invariants())
                
            if (data_even_now is not None):
                self.intermediate_sizes_.append([data_even_now.actual_sizes_, data_odd_now.actual_sizes_])
                
        self.fitted_ = True
        
    def transform(self, coefficients, return_only_invariants = False):
        if (not self.fitted_):
            raise NotFittedError("instance of {} is not fitted. It can not transform anything".format(type(self).__name__))
        data_even_0, data_odd_0 = self.initial_transformer_.transform(coefficients)
        data_even_0, data_odd_0 = self.initial_pca_.transform(data_even_0, data_odd_0)
        
        
        all_invariants = [data_even_0.get_invariants()]
        data_even_now, data_odd_now = data_even_0, data_odd_0
       
        all_even_covariants = [data_even_0]
        all_odd_covariants = [data_odd_0]
        for i in range(len(self.blocks_)):
            data_even_now, data_odd_now, invariants_even_now = self.blocks_[i].transform(data_even_now, data_odd_now, data_even_0, data_odd_0, all_even_covariants, all_odd_covariants, all_invariants)
            
            all_even_covariants.append(data_even_now)
            all_odd_covariants.append(data_odd_now)
            
            if (invariants_even_now is not None):
                all_invariants.append(invariants_even_now)
            else:
                all_invariants.append(data_even_now.get_invariants())
        
        if (return_only_invariants):
            return all_invariants
        else:
            return data_even_now, data_odd_now, all_invariants
        
    def is_fitted(self):
        return self.fitted_