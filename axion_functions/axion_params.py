import numpy as np
from scipy import integrate
from cosmology.basic_cosmology import func_rho_comp_0
from axion_cutoff_mass import func_beta2
from halo_model.halo_bias import func_halo_bias
from halo_model.halo_mass_function import func_halo_mass_function
from halo_model.axion_density_profile import func_central_density_param, MaxofMc
from copy import deepcopy

def func_axion_param_dic(M, cosmo_dic, power_spec_dic_sigma, eta_given=False):
    """
    generate dictionary with parameters for axions
    M_halo is the mass of the cold matter halo in solar_mass/h
    """
    #generate dictionary
    axion_param_dic = {}
    axion_param_dic['beta1'] = 1
    axion_param_dic['beta2'] = func_beta2(cosmo_dic, power_spec_dic_sigma, axion_dic = 'ignore')
    #central density parameter, to ensure, that the axion halo has the correct mass
    axion_param_dic['M_int'] = deepcopy(M)
    axion_param_dic['central_dens'] = func_central_density_param(axion_param_dic['M_int'], cosmo_dic, power_spec_dic_sigma, eta_given=eta_given, axion_dic = axion_param_dic)
        
    #for some halo mass no central density parameter can be found, ie there is no axion halo for this halo mass and M_int must be reduced
    axion_param_dic['M_int'] = axion_param_dic['M_int'] * np.where(np.array(axion_param_dic['central_dens']) <= 0, 0, 1) #set mass to zero, if central densit param is zero
    axion_param_dic['M_int'] = axion_param_dic['M_int'][axion_param_dic['M_int'] != 0.0] #delete all zero halo masses
    axion_param_dic['central_dens'] = np.array(axion_param_dic['central_dens'])[np.array(axion_param_dic['central_dens']) != 0.0] #delete all zero central density params
    
    #axion halo mass, given by the Max(Mc) relation
    cdm_frac = 1 - cosmo_dic['omega_ax_0']/cosmo_dic['omega_m_0'] # 1 - ax_frac = 1 - f
    axion_param_dic['M_ax'] = MaxofMc(axion_param_dic['M_int'], axion_param_dic['beta1'], axion_param_dic['beta2'], cosmo_dic['z'], cosmo_dic['omega_m_0'], cdm_frac, cosmo_dic['h'], cosmo_dic['m_ax'])
    
    #not all axions cluster. Compute clustered fraction by f = 1/\rho_ax * int_Mcut^\inf n(M)*b(M)*M_ax(M) dM, see masterthesis eq.
    k = power_spec_dic_sigma['k']
    PS_cold = power_spec_dic_sigma['cold']
    integrand_arr = func_halo_mass_function(axion_param_dic['M_int'], k, PS_cold , cosmo_dic, cosmo_dic['Omega_db_0'], cosmo_dic['Omega_db_0']) * \
                    axion_param_dic['M_ax'] * \
                    func_halo_bias(axion_param_dic['M_int'], k, PS_cold, cosmo_dic, cosmo_dic['Omega_db_0'])
    axion_param_dic['frac_cluster'] = integrate.simps(y= integrand_arr, x = axion_param_dic['M_int'])/ func_rho_comp_0(cosmo_dic['Omega_ax_0'])
    
    return axion_param_dic