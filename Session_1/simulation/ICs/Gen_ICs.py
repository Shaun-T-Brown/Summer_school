import numpy as np 
import matplotlib.pyplot as plt 
import h5py as h5
from scipy import stats

def gen_IC(M,c,m_p, R_max = 4):

	#define analytic properties of NFW profile
	rho_crit = 2.7754*0.674**2*10**11 # in units of M_sun / Mpc**(-3)
	G = 4.300*10**-9 # in units of Mpc /M_sun *(km/s)^2
	R200 = (M/(4/3*np.pi*200*rho_crit))**(1/3)


	#analytic cummulative distribution, for getting density profile
	x=np.logspace(-3,np.log10(R_max),1000)
	cum_pdf = np.log(1+c*x)-x/(1/c+x)
	cum_pdf=np.insert(cum_pdf,0,0.0)
	x=np.insert(x,0,0.0)
	cum_pdf/=cum_pdf[-1]
	
	#numerically solve jeans equation to get velocity disperions
	rho_0 = c**3*M/(4*np.pi*R200**3*(np.log(1+c)-c/(1+c)))
	M_int = 4*np.pi*R200**3*rho_0*(np.log(1+c*x)-c*x/(1+c*x))/c**3
	rho = rho_0/(x*c*(1+x*c)**2)
	drho = rho_0/R200*(-c/((c*x)**2*(1+c*x)**2) - 2*c/(c*x*(1+c*x)**3))
	sigma2 = -G*M_int*rho/((x*R200)**2*drho) #velocity dispersion
	
	#plt.figure()
	#plt.plot(x,sigma2**0.5)
	#plt.show()
	#exit()
	#number of particles needed
	M_tot = M/(200/3*rho_crit)*rho_0*(np.log(1+c*R_max)-R_max/(1/c+R_max))/c**3
	N=int(M_tot/m_p)
	print('%d particles for halo'%N)
	#generate particle positions
	pos_spherical = np.random.random(size=(N,3)) #r,theta, phi

	#generate radii of particle to match the input NFW profile
	pos_spherical[:,0] = np.interp(pos_spherical[:,0],cum_pdf,x)
	#generate angles to be isotropic
	pos_spherical[:,2]*=2*np.pi
	pos_spherical[:,1] = np.arccos(2*pos_spherical[:,1]-1)
	
	#convert to cartesian
	pos_cartesian = np.zeros(pos_spherical.shape)
	pos_cartesian[:,0] = pos_spherical[:,0]*np.sin(pos_spherical[:,1])*np.cos(pos_spherical[:,2])
	pos_cartesian[:,1] = pos_spherical[:,0]*np.sin(pos_spherical[:,1])*np.sin(pos_spherical[:,2])
	pos_cartesian[:,2] = pos_spherical[:,0]*np.cos(pos_spherical[:,1])

	pos_cartesian*=R200 #convert from normalised units
	
	
	#generate velocities
	vel = np.zeros((N,3))
	vel[:,0] = np.random.normal(loc=0.0,scale = np.interp(pos_spherical[:,0],x,sigma2**0.5))
	vel[:,1] = np.random.normal(loc=0.0,scale = np.interp(pos_spherical[:,0],x,sigma2**0.5))
	vel[:,2] = np.random.normal(loc=0.0,scale = np.interp(pos_spherical[:,0],x,sigma2**0.5))

	return(pos_cartesian,vel)

def write_ICs(pos,vel,part_id,part_mass,file_name):

	N=len(pos)
	h = h5.File(file_name,'w')

	#set up groups
	group = h.create_group('PartType1')
	header = h.create_group('Header')

	#add data
	group.create_dataset('Coordinates',(pos.shape),dtype='f',data = pos)
	group.create_dataset('Velocities',(pos.shape),dtype='f',data = vel)
	group.create_dataset('Masses',(len(pos),),dtype='f',data = np.ones(len(pos))*part_mass)
	group.create_dataset('ParticleIDs',(len(pos),),dtype='i',data = part_id)

	#deal with header info
	header.attrs['Dimension'] = 3
	header.attrs['BoxSize'] = 20.0
	header.attrs['NumPart_Total'] = [0, N, 0, 0, 0, 0]
	header.attrs['NumPart_Total_HighWord'] = [0, 0, 0, 0, 0, 0]
	header.attrs['Flag_Entropy_ICs'] = 0
	return()


#define some constants
rho_crit = 2.7754*0.674**2*10**11 # in units of M_sun / Mpc**(-3)
G = 4.300*10**-9 # in units of Mpc /M_sun *(km/s)^2

#Host and satellite parameters
M_200_host = 10**12; c_host = 6;
M_200_sat = 10**11.5; c_sat = 15;
part_mass = 10**9

R_200_host = (M_200_host/(4/3*np.pi*200*rho_crit))**(1/3)
print(R_200_host)
v_circ = (G*M_200_host/R_200_host)**0.5


#Infall paramters
b=2.0 #impact parameter, in units of host R200
vel_infall = 0.8 #velocity of satellite, in units of host circular velocity

#generate intial conditions
pos_host,vel_host = gen_IC(M_200_host, c_host, part_mass)
pos_sat,vel_sat = gen_IC(M_200_sat, c_sat, part_mass)

rad = (pos_host[:,0]**2+pos_host[:,1]**2+pos_host[:,2]**2)**0.5

std,bin_edge,bin_bum=stats.binned_statistic(rad, vel_host[:,0], 'std', bins=1000)

part_ID_host = np.arange(len(pos_host),dtype=int)
part_ID_sat = np.arange(len(pos_sat),dtype=int)+len(pos_host)

#offset satellite
pos_sat[:,0]+=6*R_200_host
pos_sat[:,1]+=b*R_200_host
vel_sat[:,0]-=vel_infall*v_circ

boxsize=20
#offset to the middle of the box for swift
pos_host+=boxsize/2
pos_sat+=boxsize/2

#save initial conditions
write_ICs(pos_host,vel_host,part_ID_host,part_mass*10**-10,'./ICs_host.hdf5')
write_ICs(pos_sat,vel_sat,part_ID_sat,part_mass*10**-10,'./ICs_sat.hdf5')
write_ICs(np.append(pos_host,pos_sat,axis=0),np.append(vel_host,vel_sat,axis=0),np.append(part_ID_host,part_ID_sat),part_mass*10**-10,'./ICs_merger.hdf5')
