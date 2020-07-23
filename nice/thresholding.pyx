from libc.math cimport sin, M_PI, sqrt, fmax
cimport cython
import numpy as np
#from cython.parallel cimport prange
from nice_utilities cimport min_c, abs_c, max_c
cdef double sqrt_2 = sqrt(2.0)
#from nice_utilities import Data


cdef get_thresholded_task(double[:, :] first_importances, int[:] first_actual_sizes,
                           double[:, :] second_importances, int[:] second_actual_sizes,
                           double threshold, int known_num, int l_max):
    
    ans = np.empty([known_num, 4], dtype = np.int32)
    
    importances = np.empty([known_num])
    
    cdef int[:, :] ans_view = ans
    
    cdef int l1, l2, first_ind, second_ind, lambd
    cdef int pos = 0
   
    for l1 in range(l_max + 1):
        for l2 in range(l_max + 1):
            for first_ind in range(first_actual_sizes[l1]):
                for second_ind in range(second_actual_sizes[l2]):
                    if (first_importances[first_ind, l1] * second_importances[second_ind, l2] >= threshold):                     
                        ans_view[pos, 0] = first_ind
                        ans_view[pos, 1] = l1
                        ans_view[pos, 2] = second_ind
                        ans_view[pos, 3] = l2                           
                        importances[pos] = first_importances[first_ind, l1] * second_importances[second_ind, l2]
                        pos += 1
   
    return [ans[:pos], importances[:pos]]                       
                       
                                      
cpdef get_thresholded_tasks(first_even, first_odd, second_even, second_odd, int desired_num, int l_max):    
  
    cdef double threshold_even
    cdef int num_even_even, num_odd_odd
    threshold_even, num_even_even, num_odd_odd = get_threshold(first_even.importances_, first_even.actual_sizes_,
                                                               second_even.importances_, second_even.actual_sizes_,
                                                               first_odd.importances_, first_odd.actual_sizes_,
                                                               second_odd.importances_, second_odd.actual_sizes_,
                                                               desired_num)
    
    cdef double threshold_odd
    cdef int num_even_odd, num_odd_even
    threshold_odd, num_even_odd, num_odd_even = get_threshold(first_even.importances_, first_even.actual_sizes_,
                                                              second_odd.importances_, second_odd.actual_sizes_,
                                                              first_odd.importances_, first_odd.actual_sizes_,
                                                              second_even.importances_, second_even.actual_sizes_,
                                                              desired_num)        
      
    
    
    task_even_even = get_thresholded_task(first_even.importances_, first_even.actual_sizes_,
                                          second_even.importances_, second_even.actual_sizes_, 
                                          threshold_even, num_even_even, l_max)
    
    task_odd_odd = get_thresholded_task(first_odd.importances_, first_odd.actual_sizes_,
                                        second_odd.importances_, second_odd.actual_sizes_,
                                        threshold_even, num_odd_odd, l_max)
    
    task_even_odd = get_thresholded_task(first_even.importances_, first_even.actual_sizes_,
                                         second_odd.importances_, second_odd.actual_sizes_,
                                         threshold_odd, num_even_odd, l_max)
    
    task_odd_even = get_thresholded_task(first_odd.importances_, first_odd.actual_sizes_,
                                         second_even.importances_, second_even.actual_sizes_,
                                         threshold_odd, num_odd_even, l_max)
    
    return task_even_even, task_odd_odd, task_even_odd, task_odd_even
                           
                           
                           
cdef get_threshold(double[:, :] first_importances_1, int[:] first_actual_sizes_1,
                   double[:, :] second_importances_1, int[:] second_actual_sizes_1,
                   double[:, :] first_importances_2, int[:] first_actual_sizes_2,
                   double[:, :] second_importances_2, int[:] second_actual_sizes_2,
                   int desired_num, int min_iterations = 50):
    
    
    if (desired_num == -1):
        num_1_1 = get_total_num_full(first_importances_1, first_actual_sizes_1, second_importances_1, second_actual_sizes_1, -1.0)  
        num_2_2 = get_total_num_full(first_importances_2, first_actual_sizes_2, second_importances_2, second_actual_sizes_2, -1.0)  
        return -1.0, num_1_1, num_2_2
    
    cdef double left = -1.0
    cdef double first = get_upper_threshold(first_importances_1, first_actual_sizes_1, second_importances_1, second_actual_sizes_1) + 1.0
    cdef double second = get_upper_threshold(first_importances_2, first_actual_sizes_2, second_importances_2, second_actual_sizes_2) + 1.0
    
    cdef double right = fmax(first, second)
    cdef double middle = (left + right) / 2.0
    cdef int num_now, num_previous = -1
    cdef int num_it_no_change = 0
    while (True):
        middle = (left + right) / 2.0
        num_now = get_total_num_full(first_importances_1, first_actual_sizes_1, second_importances_1, second_actual_sizes_1, middle) + get_total_num_full(first_importances_2, first_actual_sizes_2, second_importances_2, second_actual_sizes_2, middle)
        
        if (num_now == desired_num):
            break
        if (num_now > desired_num):
            left = middle
        if (num_now < desired_num):
            right = middle
            
        if (num_now == num_previous):
            num_it_no_change += 1
            if (num_it_no_change > min_iterations):
                break
        else:
            num_it_no_change = 0
        num_previous = num_now
            
    num_1_1 = get_total_num_full(first_importances_1, first_actual_sizes_1, second_importances_1, second_actual_sizes_1, middle)  
    num_2_2 = get_total_num_full(first_importances_2, first_actual_sizes_2, second_importances_2, second_actual_sizes_2, middle)  
    return middle, num_1_1, num_2_2
    
    
cdef double get_upper_threshold(double[:, :] first_importances, int[:] first_actual_sizes, 
                             double[:, :] second_importances, int[:] second_actual_sizes):
    cdef double ans = 0.0
    cdef int l1, l2
    cdef int second_size = second_importances.shape[1]
    
    for l1 in range(first_importances.shape[1]):
        for l2 in range(second_size):
            if (first_actual_sizes[l1] > 0) and (second_actual_sizes[l2] > 0):
                if (first_importances[0, l1] * second_importances[0, l2] > ans):
                    ans = first_importances[0, l1] * second_importances[0, l2]
                    
    return ans
                  
    
cdef int get_total_num_full(double[:, :] first_importances, int[:] first_actual_sizes,
                            double[:, :] second_importances, int[:] second_actual_sizes,
                            double threshold):
    cdef int l1, l2
    cdef int second_size = second_importances.shape[1]
    cdef int res = 0
    for l1 in range(first_importances.shape[1]):
        for l2 in range(second_size):
            if (first_actual_sizes[l1] > 0) and (second_actual_sizes[l2] > 0):
                res += get_total_num(first_importances[:first_actual_sizes[l1], l1],
                                     second_importances[:second_actual_sizes[l2], l2], threshold)
            
    return res
        
cdef int get_total_num(double[:] a, double[:] b, double threshold):
    cdef int b_size = b.shape[0]
    cdef int i, j, ans
    i = 0
    j = b_size
    ans = 0
    for i in range(a.shape[0]):
        while ((j > 0) and (a[i] * b[j - 1] < threshold)):
            j -= 1
        ans += j
    return ans
