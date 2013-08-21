"""Reinforcement learning parts of the rrl package. This mainly
includes the Actor-Critic-Design.

"""

import PuPy
import numpy as np
import cPickle as pickle

class Plant(object):
    """A template for Actor-Critic *plants*. The *Plant* describes the
    interaction of the Actor-Critic with the environment. Given a robot
    which follows a certain *Policy*, the environment generates rewards
    and robot states.
    
    An additional instance to :py:class:`PuPy.Normalization` may be 
    supplied in ``norm`` for normalizing sensor values.
    """
    def __init__(self, state_space_dim=None, norm=None):
        self._state_space_dim = state_space_dim
        self.set_normalization(norm)
    
    def state_input(self, state, action):
        """Return the state-part of the critic input
        (i.e. the reservoir input).
        
        The state-part is derived from the current robot ``state`` and
        possibly also its ``action``. As return format, a Nx1 numpy
        vector is expected, where 2 dimensions should exist (e.g.
        :py:meth:`numpy.atleast_2d`).
        
        Although the reservoir input will consist of both, the *state*
        and *action*, this method must only return the *state* part of
        it.
        
        """
        raise NotImplementedError()
    
    def reward(self, epoch):
        """A reward generated by the *Plant* based on the current
        sensor readings in ``epoch``. The reward is single-dimensional.
        
        The reward is evaluated in every step. It builds the foundation
        of the approximated return.
        """
        raise NotImplementedError()
    
    def state_space_dim(self):
        """Return the dimension of the state space.
        This value is equal to the size of the vector returned by
        :py:meth:`state_input`.
        """
        if self._state_space_dim is None:
            raise NotImplementedError()
        return self._state_space_dim
    
    def set_normalization(self, norm):
        """Set the normalization instance to ``norm``."""
        if norm is None:
            norm = PuPy.Normalization()
        self.normalization = norm

class Policy(object):
    """A template for Actor-Critic *policies*. The *Policy* defines how
    an action is translated into a control (motor) signal. It
    continously receives action updates from the *Critic* which it has
    to digest.
    
    An additional instance to :py:class:`PuPy.Normalization` may be 
    supplied in ``norm`` for normalizing sensor values.
    """
    def __init__(self, action_space_dim=None, norm=None):
        self._action_space_dim = action_space_dim
        self.set_normalization(norm)
    
    def initial_action(self):
        """Return the initial action. A valid action must be returned
        since the :py:class:`ActorCritic` relies on the format.
        
        The action has to be a 2-dimensional numpy vector, with both
        dimensions available.
        """
        raise NotImplementedError()
    
    def update(self, action_upd):
        """Update the *Policy* according to the current action update
        ``action_upd``, which was in turn computed by the
        :py:class:`ActorCritic`.
        """
        raise NotImplementedError()
    
    def get_iterator(self, time_start_ms, time_end_ms, step_size_ms):
        """Return an iterator for the *motor_target* sequence, according
        to the current action configuration.
        
        The *motor_targets* glue the *Policy* and *Plant* together.
        Since they are applied in the robot and effect the sensor
        readouts, they are an "input" to the environment. As the targets
        are generated as effect of the action update, they are an output
        of the policy.
        
        """
        raise NotImplementedError()
    
    def action_space_dim(self):
        """Return the dimension of the action space.
        This value is equal to the size of the vector returned by
        :py:meth:`initial_action`.
        """
        if self._action_space_dim is None:
            raise NotImplementedError()
        return self._action_space_dim
    
    def reset(self):
        """Undo any policy updates."""
        raise NotImplementedError()
    
    def set_normalization(self, norm):
        """Set the normalization instance to ``norm``."""
        if norm is None:
            norm = PuPy.Normalization()
        self.normalization = norm

class _ConstParam:
    """Stub for wrapping constant values into an executable function."""
    def __init__(self, value):
        self._value = value
    def __call__(self, time0=None, time1=None):
        """Return the constant value."""
        return self._value

class ActorCritic(PuPy.PuppyActor):
    """Actor-critic design.
    
    The Actor-Critic estimates the return function
    
    .. math::
        J_t = \sum\limits_{k=t}^{T} \gamma^k r_{t+k+1}
    
    while the return is optimized at the same time. This is done by
    incrementally updating the estimate for :math:`J_t` and choosing
    the next action by optimizing the return in a single step. See
    [ESN-ACD]_ for details.
    
    ``reservoir``
        A reservoir instance compliant with the interface of
        :py:class:`SparseReservoirNode`. Specifically, must provide
        a *reset* method and *reset_states* must be :py:const:`False`.
        The input dimension must be compliant with the specification
        of the ``action``.
    
    ``readout``
        The reservoir readout function. An instance of ``PlainRLS`` is
        expected. Note that the readout must include a bias. The
        dimensions of ``reservoir`` and ``readout``  must match and the
        output of the latter must be single dimensional.
    
    ``plant``
        An instance of :py:class:`Plant`. The plant defines the
        interaction with the environment.
    
    ``policy``
        An instance of :py:class:`Policy`. The policy defines the
        interaction with the robot's actuators.
    
    ``gamma``
        Choice of *gamma* in the return function. May be a constant or
        a function of the time (relative to the episode start).
        
    ``alpha``
        Choice of *alpha* in the action update. May be a constant or a
        function of the time (relative to the episode start).
        
        The corresponding formula is
        
        .. math::
            a_{t+1} = a_{t} + \\alpha \\frac{\partial J_t}{\partial a_t}
        
        See [ESN-ACD]_ for details.
        
    ``norm``
        A :py:class:`PuPy.Normalization` for normalization purposes.
        Note that the parameters for *a_curr* and *a_next* should be
        exchangable, since it's really the same kind of 'sensor'.
    
    """
    def __init__(self, plant, policy, gamma=1.0, alpha=1.0, init_steps=1, norm=None):
        super(ActorCritic, self).__init__()
        self.plant = plant
        self.policy = policy
        if norm is None:
            norm = PuPy.Normalization()
        
        self.normalizer = norm
        self.plant.set_normalization(self.normalizer)
        self.policy.set_normalization(self.normalizer)
        self.set_alpha(alpha)
        self.set_gamma(gamma)
        self.num_episode = 0
        self.new_episode()
        self._init_steps = init_steps
        
        # Check assumptions
        assert self.policy.initial_action().shape[0] >= 1
        assert self.policy.initial_action().shape[1] == 1
    
    def new_episode(self):
        """Start a new episode of the same experiment. This method can
        also be used to initialize the *ActorCritic*, for example when
        it is loaded from a file.
        """
        self.num_episode += 1
        self.a_curr = self.policy.initial_action()
        self._motor_action_dim = self.policy.action_space_dim()
        self.s_curr = dict()
        self.num_step = 0
    
    def init_episode(self, epoch, time_start_ms, time_end_ms, step_size_ms):
        self.s_curr = epoch
        self._pre_increment_hook(epoch)
        return self.policy.get_iterator(time_start_ms, time_end_ms, step_size_ms)
    
    def __call__(self, epoch, time_start_ms, time_end_ms, step_size_ms):
        """One round in the actor-critic cycle. The current observations
        are given in *epoch* and the timing information in the rest of
        the parameters. For a detailed description of the parameters,
        see :py:class:`PuPy.PuppyActor`.
        
        .. todo::
            Detailed description of the algorithm.
        
        """
        if self.num_step <= self._init_steps:
            self.num_step += 1
            return self.init_episode(epoch, time_start_ms, time_end_ms, step_size_ms)
        
        """
        if self.num_step < 3:
            self.num_step += 1
            self.s_curr = epoch
            self._pre_increment_hook(epoch)
            return self.policy.get_iterator(time_start_ms, time_end_ms, step_size_ms)
        """
        
        # extern through the robot:
        # take action (a_curr = a_next in the previous run)
        # observe sensors values produced by the action (a_curr = previous a_next)
        
        # Generate reinforcement signal U(k), given in(k)
        #reward = self.plant.reward(epoch)
        reward = self.plant.reward(self.s_curr)
        # It's not clear, which reward should be the input to the critic:
        # While the ACD papers imply the reward of time step n, the book
        # by Sutton/Barto indicate the reward as being from the next
        # state, n+1. Experiments indicate that it doesn't really matter.
        # To be consistent with other work, I go with time n.
        
        # do the actual work
        a_next = self._step(self.s_curr, epoch, self.a_curr, reward)
        
        # increment
        self.a_curr = a_next
        self.s_curr = epoch
        self.num_step += 1
        
        # return next action
        self.policy.update(a_next)
        return self.policy.get_iterator(time_start_ms, time_end_ms, step_size_ms)
    
    def _step(self, s_curr, s_next, a_curr, reward):
        """Execute one step of the actor and return the next action.
        
        ``s_curr``
            Previous observed state. :py:keyword:`dict`, same as ``epoch``
            of the :py:meth:`__call__`.
        
        ``s_next``
            Latest observed state. :py:keyword:`dict`, same as ``epoch``
            of the :py:meth:`__call__`.
        
        ``reward``
            Reward of ``s_next``
        
        """
        raise NotImplementedError()
    
    def _pre_increment_hook(self, epoch, **kwargs):
        """Template method for subclasses.
        
        Before the actor-critic cycle increments, this method is invoked
        with all relevant locals of the :py:meth:`ADHDP.__call__`
        method.
        """
        pass
    
    def _next_action_hook(self, a_next):
        """Postprocessing hook, after the next action ``a_next`` was
        proposed by the algorithm. Must return the possibly altered
        next action in the same format."""
        #from math import pi
        #a_next = np.random.uniform(-pi/2.0, pi/2.0, size=self.a_curr.shape)
        #a_next = a_next % (2*pi)
        return a_next
    
    def save(self, pth):
        """Store the current instance in a file at ``pth``.
        
        .. note::
            If ``alpha`` or ``gamma`` was set to a user-defined
            function, make sure it's pickable. Especially, anonymous
            functions (:keyword:`lambda`) can't be pickled.
        
        """
        f = open(pth, 'w')
        pickle.dump(self, f)
        f.close()
    
    @staticmethod
    def load(pth):
        """Load an instance from a file ``pth``.
        """
        f = open(pth, 'r')
        cls = pickle.load(f)
        cls.new_episode()
        return cls
    
    def set_alpha(self, alpha):
        """Define a value for ``alpha``. May be either a constant or
        a function of the time.
        """
        if callable(alpha):
            self.alpha = alpha
        else:
            self.alpha = _ConstParam(alpha)
    
    def set_gamma(self, gamma):
        """Define a value for ``gamma``. May be either a constant or
        a function of the time.
        """
        if callable(gamma):
            self.gamma = gamma
        else:
            self.gamma = _ConstParam(gamma)

class ADHDP(ActorCritic):
    """
    """
    def __init__(self, reservoir, readout, *args, **kwargs):
        self.reservoir = reservoir
        self.readout = readout
        super(ADHDP, self).__init__(*args, **kwargs)
        
        # Check assumptions
        assert self.reservoir.reset_states == False
        assert self.reservoir.get_input_dim() == self.policy.action_space_dim() + self.plant.state_space_dim()
        #assert self.readout.beta.shape == (self.reservoir.output_dim + 1, 1)
        #assert self.readout.beta.shape == (self.reservoir.output_dim + self.policy.action_space_dim() + self.plant.state_space_dim() + 1, 1) # FIXME: Input/Output ESN Model
        assert self.reservoir.get_input_dim() >= self.policy.initial_action().shape[0]
    
    def new_episode(self):
        """Start a new episode of the same experiment. This method can
        also be used to initialize the *ActorCritic*, for example when
        it is loaded from a file.
        """
        self.reservoir.reset()
        super(ADHDP, self).new_episode()
    
    def _critic_eval(self, state, action, simulate, action_name='a_curr'):
        """Evaluate the critic at ``state`` and ``action``."""
        in_state = self.plant.state_input(state)
        action_nrm = self.normalizer.normalize_value(action_name, action)
        #in_state += np.random.normal(scale=0.05, size=in_state.shape)
        r_input = np.vstack((in_state, action_nrm)).T
        r_state = self.reservoir(r_input, simulate=simulate)
        #o_input = np.hstack((r_state, r_input)) # FIXME: Input/Output ESN Model
        #j_curr = self.readout(o_input) # FIXME: Input/Output ESN Model
        j_curr = self.readout(r_state)
        return r_input, r_state, j_curr
    
    def _critic_deriv(self, r_state):
        """Return the critic's derivative at ``r_state``."""
        e = (np.ones(r_state.shape) - r_state**2).T # Nx1
        k = e * self.reservoir.w_in[:, -self._motor_action_dim:].toarray() # Nx1 .* NxA => NxA
        deriv = self.readout.beta[1:].T.dot(k) #  LxA
        #deriv = self.readout.beta[1:-i_curr.shape[1]].T.dot(k) #  LxA  # FIXME: Input/Output ESN Model
        #deriv += self.readout.beta[-self._motor_action_dim:].T # FIXME: Input/Output ESN Model
        deriv = deriv.T # AxL
        scale = self.normalizer.get('a_curr')[1]
        deriv /= scale # Derivative denormalization
        return deriv
    
    def _step(self, s_curr, s_next, a_curr, reward):
        """Execute one step of the actor and return the next action.
        
        ``s_next``
            Latest observed state. :py:keyword:`dict`, same as ``s_next``
            of the :py:meth:`__call__`.
        
        ``s_curr``
            Previous observed state. :py:keyword:`dict`, same as ``s_next``
            of the :py:meth:`__call__`.
        
        ``reward``
            Reward of ``s_next``
        
        """
        # ESN-critic, first instance: in(k) => J(k)
        i_curr, x_curr, j_curr = self._critic_eval(s_curr, a_curr, simulate=False, action_name='a_curr')
        
        # Next action
        deriv = self._critic_deriv(x_curr)
        
        # gradient training of action (acc. to eq. 10)
        a_next = a_curr + self.alpha(self.num_episode, self.num_step) * deriv # FIXME: Denormalization of deriv (scale*deriv)
        a_next = self._next_action_hook(a_next)
        
        # ESN-critic, second instance: in(k+1) => J(k+1)
        i_next, x_next, j_next = self._critic_eval(s_next, a_next, simulate=True, action_name='a_next')
        
        # TD_error(k) = J(k) - U(k) - gamma * J(k+1)
        err = reward + self.gamma(self.num_episode, self.num_step) * j_next - j_curr
        
        # One-step RLS training => Trained ESN
        self.readout.train(x_curr, e=err) 
        #self.readout.train(o_curr, e=err) # FIXME: Input/Output ESN Model
        
        # increment hook
        self._pre_increment_hook(
            s_next,
            reward=np.atleast_2d([reward]).T,
            deriv=deriv.T,
            err=err.T,
            readout=self.readout.beta.T,
            #psiInv=self.readout._psiInv.reshape((1, self.readout._psiInv.shape[0]**2)),
            gamma=np.atleast_2d([self.gamma(self.num_episode, self.num_step)]).T,
            i_curr=i_curr,
            x_curr=x_curr,
            j_curr=j_curr,
            a_curr=a_curr.T,
            i_next=i_next,
            x_next=x_next,
            j_next=j_next,
            a_next=a_next.T
            )
        
        # increment
        return a_next

class CollectingADHDP(ADHDP):
    """Actor-Critic design with data collector.
    
    A :py:class:`PuPy.PuppyCollector` instance is created for recording
    sensor data and actor-critic internals together. The file is stored
    at ``expfile``.
    """
    def __init__(self, expfile, *args, **kwargs):
        self.expfile = expfile
        self.collector = None
        
        self.headers = None
        if 'additional_headers' in kwargs:
            self.headers = kwargs.pop('additional_headers')
        
        super(CollectingADHDP, self).__init__(*args, **kwargs)
    
    def _pre_increment_hook(self, epoch, **kwargs):
        """Add the *ADHDP* internals to the epoch and use the
        *collector* to save all the data.
        """
        ep_write = epoch.copy()
        for key in kwargs:
            ep_write[key] = kwargs[key]
        
        self.collector(ep_write, 0, 1, 1)
    
    def save(self, pth):
        """Save the instance without the *collector*.
        
        .. note::
            When an instance is reloaded via :py:meth:`ADHDP.load`
            a new group will be created in *expfile*.
        
        """
        # Shift collector to local
        collector = self.collector
        self.collector = None
        super(CollectingADHDP, self).save(pth)
        # Shift collector to class
        self.collector = collector

    def new_episode(self):
        """Do everything the parent does and additionally reinitialize
        the collector. The reservoir weights are stored as header
        information.
        """
        super(CollectingADHDP, self).new_episode()
        
        # init/reset collector
        if self.collector is not None:
            del self.collector
        
        self.collector = PuPy.PuppyCollector(
            actor=None,
            expfile=self.expfile,
            headers=self.headers
            #headers={
            #    # FIXME: Store complete reservoir or at least include the bias
            #    # FIXME: Doesn't work with too large reservoirs (>80 nodes)? This is because of the size limit of HDF5 headers
            #    #        Could be stored as dataset though...
            #    'r_weights': self.reservoir.w.todense(),
            #    'r_input'  : self.reservoir.w_in.todense()
            #    }
        )
    
    def __del__(self):
        del self.collector
