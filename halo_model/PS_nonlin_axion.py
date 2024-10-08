"""functions for my full axion halo model and simpified halo models"""

import numpy as np
from scipy import integrate
from cosmology.basic_cosmology import func_rho_comp_0
from halo_bias import func_halo_bias
from halo_mass_function import func_halo_mass_function
from cold_density_profile import func_dens_profile_kspace
from axion_density_profile import func_dens_profile_ax_kspace
from PS_nonlin_cold import func_non_lin_PS_matter


def func_full_halo_model_ax(M, power_spec_dic, power_spec_dic_sigma, cosmo_dic, hmcode_dic, axion_dic, 
                            alpha = False, eta_given = False, one_halo_damping = True, two_halo_damping = False):
    """ 
    My Full Halo Model with Axions, see my masterhesis eq 5.2-5.10 to see the full formula
    all modifications form HMcode2020 https://arxiv.org/abs/2009.01858 can be used (if wanted)
    by default use only the damping in the one halo term on large scales (for all parts) 
    to ensure the correct behaviour on large scales
    M in solar_mass/h
    in power_spec_dic and power_spec_dic_sigma the PS and k's are stored 
    and all units are either in (Mpc/h)^3 or h/Mpc
    NOTE: Two PS dicionaries are needed bacause we have to be carefull with the calulation of sigma
    returns total non-linear matter power spectrum in (Mpc/h)^3 at k
    """ 
    k = power_spec_dic['k']
    PS_cold = power_spec_dic['cold']
    PS_ax = power_spec_dic['power_axion']
    k_sigma = power_spec_dic_sigma['k']
    PS_cold_sigma = power_spec_dic_sigma['cold']
    alpha_param = hmcode_dic['alpha']   
    
    ############# Cold matter term ##########
    PS_cold_nonlin = func_non_lin_PS_matter(M, k, PS_cold, k_sigma, PS_cold_sigma, cosmo_dic, hmcode_dic, cosmo_dic['Omega_db_0'], cosmo_dic['Omega_db_0'], 
                                            alpha = alpha, eta_given = eta_given, ax_one_halo=False, one_halo_damping = one_halo_damping, two_halo_damping = two_halo_damping)[0]
    
    ## Compute all ingridients for the diff halo model parts##
    halo_mass_func_arr = func_halo_mass_function(M, k_sigma, PS_cold_sigma, cosmo_dic, 
                                                 cosmo_dic['Omega_db_0'], cosmo_dic['Omega_db_0']) # for the integral over M ~[0, inf]
    halo_mass_func_arr_2 = func_halo_mass_function(axion_dic['M_int'], k_sigma, PS_cold_sigma, cosmo_dic, 
                                                   cosmo_dic['Omega_db_0'], cosmo_dic['Omega_db_0']) # for the integral over reduced array M_int ~ M
    dens_profile_cold_arr = func_dens_profile_kspace(M, k, k_sigma, PS_cold_sigma, cosmo_dic, hmcode_dic, cosmo_dic['Omega_db_0'], 
                                                     cosmo_dic['Omega_db_0'], eta_given = eta_given) # for the integral over M ~[0, inf]
    dens_profile_cold_arr_2 = func_dens_profile_kspace(axion_dic['M_int'], k, k_sigma, PS_cold_sigma, cosmo_dic, hmcode_dic, cosmo_dic['Omega_db_0'], 
                                                       cosmo_dic['Omega_db_0'], eta_given=eta_given) # for the integral over reduced array M_int ~ M
    dens_profile_ax_arr_2 = func_dens_profile_ax_kspace(k, axion_dic['M_int'], cosmo_dic, power_spec_dic, axion_dic['central_dens'],
                                                        eta_given=False) # this integral in only in the reduced one
    halo_bias_arr = func_halo_bias(M, k_sigma, PS_cold_sigma, cosmo_dic, cosmo_dic['Omega_db_0']) # for the integral over M ~[0, inf]
    halo_bias_arr_2 = func_halo_bias(axion_dic['M_int'], k_sigma, PS_cold_sigma, cosmo_dic, cosmo_dic['Omega_db_0']) # for the integral over reduced array M_int ~ M
    
    ### Cross one halo term, Eq. 35 in Vogt 2022, axion_dic['M_int'] is just the M_c array ###
    integrand_arr_one_halo_cross = axion_dic['M_int'][:, None] * axion_dic['M_ax'][:, None] * halo_mass_func_arr_2[:, None]\
                                   * dens_profile_cold_arr_2 * dens_profile_ax_arr_2 # integral over reduced array M_int ~ M
    if one_halo_damping == True:
        one_halo_term_cross = (k/hmcode_dic['k_star'])**4 / (1+(k/hmcode_dic['k_star'])**4) \
                          * integrate.simps(integrand_arr_one_halo_cross, x = axion_dic['M_int'], axis = 0) \
                          / (func_rho_comp_0(cosmo_dic['Omega_db_0']) 
                          * func_rho_comp_0(cosmo_dic['Omega_ax_0']) * axion_dic['frac_cluster'])
    else:
        one_halo_term_cross = integrate.simps(integrand_arr_one_halo_cross, x = axion_dic['M_int'], axis = 0) \
                          / (func_rho_comp_0(cosmo_dic['Omega_db_0']) 
                          * func_rho_comp_0(cosmo_dic['Omega_ax_0']) * axion_dic['frac_cluster'])
    
    ### Cross two halo term ###
    integrand_arr_two_halo_cross = M[:, None] * halo_mass_func_arr[:, None] * halo_bias_arr[:, None] * dens_profile_cold_arr  # integral over M ~[0, inf], Eq. 36, first line
    integrand_arr_two_halo_2_cross = axion_dic['M_ax'][:, None] * halo_mass_func_arr_2[:, None] * halo_bias_arr_2[:, None] * dens_profile_ax_arr_2 # integral over reduced array M_int ~ M, Eq. 36, second line, without P_c^L
    # Note: summand2_cross to take care of nummerical issues of the integral, see appendix A in https://arxiv.org/abs/2005.00009, note how M_1 in the denominator cancels M_1 from numerator (W_u = Mc*uc(k, Mc))
    summand2_cross = func_dens_profile_kspace(np.min(M), k, k_sigma, PS_cold_sigma, cosmo_dic, hmcode_dic, cosmo_dic['Omega_db_0'], cosmo_dic['Omega_db_0'], eta_given = eta_given) \
                     * ( 1 - integrate.simps(M[:, None] * halo_mass_func_arr[:, None] * halo_bias_arr[:, None], x = M, axis = 0) \
                     / func_rho_comp_0(cosmo_dic['Omega_db_0']) ) # We assume that k->0 as we need to (A.5), in which case W_u(M,k->0) = M/rhobar, i.e. u(k->) = 1
    factor2_cross = integrate.simps(integrand_arr_two_halo_cross, x = M, axis = 0) / func_rho_comp_0(cosmo_dic['Omega_db_0']) + summand2_cross # integral over Mc + additive correction
    two_halo_term_cross =  PS_cold\
                           * factor2_cross \
                           * integrate.simps(integrand_arr_two_halo_2_cross, x = axion_dic['M_int'], axis = 0) \
                           / (func_rho_comp_0(cosmo_dic['Omega_ax_0']) * axion_dic['frac_cluster']) # integral over Ma
    
    ############# Total cross term #################
    PS_total_cross = axion_dic['frac_cluster']*((one_halo_term_cross**(alpha_param[1]) + two_halo_term_cross**(alpha_param[1]))**(1/alpha_param[1]))[0, :] + (1-axion_dic['frac_cluster'])*np.sqrt(PS_ax * PS_cold_nonlin) # Eq. 32
    
    ### Axion one halo term ###
    integrand_arr_one_halo_ax =  axion_dic['M_ax'][:, None]**2 * halo_mass_func_arr_2[:, None] * np.array(dens_profile_ax_arr_2)**2 #for the integral over reduced array M_int ~ M, Eq. 37
    if one_halo_damping == True:
        one_halo_term_ax = (k/hmcode_dic['k_star'])**4 / (1+(k/hmcode_dic['k_star'])**4) \
                           * integrate.simps(integrand_arr_one_halo_ax, x = axion_dic['M_int'], axis = 0) \
                           / (func_rho_comp_0(cosmo_dic['Omega_ax_0']) * axion_dic['frac_cluster'])**2 
    else:
        one_halo_term_ax = integrate.simps(integrand_arr_one_halo_ax, x = axion_dic['M_int'], axis = 0) \
                           / (func_rho_comp_0(cosmo_dic['Omega_ax_0']) * axion_dic['frac_cluster'])**2 
        
    ### Axion two halo term ###
    integrand_arr_two_halo_ax = axion_dic['M_ax'][:, None] * halo_mass_func_arr_2[:, None] * halo_bias_arr_2[:, None] * dens_profile_ax_arr_2 #for the integral over reduced array M_int ~ M, Eq. 38
    # Again take care of nummerical issues, this time for axion 2-halo term
    factor2_ax = integrate.simps(integrand_arr_two_halo_ax, x = axion_dic['M_int'], axis = 0) / func_rho_comp_0(cosmo_dic['Omega_ax_0']) # integral over Ma (+ additive correction if need be)
    two_halo_term_ax =  PS_cold\
                        * factor2_ax\
                        * integrate.simps(integrand_arr_two_halo_ax, x = axion_dic['M_int'], axis = 0) \
                        / (func_rho_comp_0(cosmo_dic['Omega_ax_0'])) / (axion_dic['frac_cluster'])**2 # second integral over Ma 
    
    ############ Total axion term ###################
    PS_total_ax = axion_dic['frac_cluster']**2 * (one_halo_term_ax + two_halo_term_ax) \
                  + 2*(1- axion_dic['frac_cluster']) * axion_dic['frac_cluster'] * np.sqrt((one_halo_term_ax + two_halo_term_ax)*PS_ax) \
                  + (1- axion_dic['frac_cluster'])**2 * power_spec_dic['power_axion']  
    
    ##### Stick all together to get the total non-lin matter PS ####
    PS_total_matter = (cosmo_dic['Omega_db_0']/cosmo_dic['Omega_m_0'])**2 * PS_cold_nonlin \
                      + 2*cosmo_dic['Omega_db_0']*cosmo_dic['Omega_ax_0']/cosmo_dic['Omega_m_0']**2 * PS_total_cross \
                      + (cosmo_dic['Omega_ax_0']/cosmo_dic['Omega_m_0'])**2 * PS_total_ax
    
    return PS_total_matter, PS_cold_nonlin, PS_total_cross, PS_total_ax