import json
from twisted.internet import defer


class BaseTask(object):
    '''
    The base for all tasks used in mil_tasks. Lots of this class
    is just documentation for the various functions that real tasks
    can overload. Individual ROS robotics platforms should extend this
    base class to provide interfaces to the particular systems on the robot.
    '''
    nh = None
    task_runner = None

    def __init__(self, parent=None):
        '''
        Called when a new instance of a task is created. Tasks
        should be sure to call base task __init__
        def __init__(self):
            super(MyTaskClass, self).__init__()
            ...
        '''
        self.parent = parent

    @classmethod
    def name(cls):
        '''
        Override for real tasks to return a string for how the task
        with be referenced in the GUI/CLI. For example, a task implemented
        in class MyCoolMission might implement
        @classmethod
        def name(cls):
            return 'My cool task'
        '''
        return cls.__name__

    @classmethod
    def init(cls):
        '''
        Called for each when the server starts up and after the base task is
        initialized. Intended for tasks to setup subscribers, state variables,
        etc that will be shared between individual instances of a task. For example,
        a task which moves to the current position of a vision target might subscribe
        to the perception node's topic in init() so that when the task is run it already
        has the latest position.
        '''
        pass

    @classmethod
    def _init(cls, task_runner):
        '''
        Called once for the BaseTask class. Use for base class to set up move
        action clients, perception hook-ins, etc. Other BaseTask classes should first
        call this _init to setup the nodehandle:

        def _init(cls, task_runner):
            super(MyRobotBaseTask, cls)._init(cls, task_runner)
            ...
        '''
        cls.task_runner = task_runner
        cls.nh = cls.task_runner.nh

    def send_feedback(self, message):
        '''
        Send a string as feedback to any clients monitoring this task. If the task is a child
        task, it will call the send_feedback_child of its parent, allowing tasks to choose how to
        use the feedback from its children.
        '''
        if self.parent:
            self.parent.send_feedback_child(message, self)
        else:
            self.task_runner.send_feedback(message)

    def send_feedback_child(self, message, child):
        '''
        Called by child tasks when sending feedback. By default sends this feedback prefixed
        with the name of the child task.
        '''
        self.send_feedback('{}: {}'.format(child.name(), message))

    @classmethod
    def has_task(self, name):
        '''
        Returns true if the task runner has a task with specified name
        '''
        return self.task_runner.has_task(name)

    @classmethod
    def get_task(self, name):
        return self.task_runner.get_task(name)

    def run_subtask(self, name, parameters=''):
        '''
        Runs another task available to the task server, returning the defered object for the
        tasks executation.
        @param name: the name of the subtask to spawn as a string. If this task is unknown,
                     raise an exception
        @param parameters: parameters to pass to the run function of the subtask. Note,
                           this function does not call decode_parameters, so parent
                           tasks need to do this or otherwise ensure the parameters are in
                           the format expected by the child.
        '''
        if not self.has_task(name):
            raise Exception('Cannot run_subtask, \'{}\' unrecognized'.format(name))
        task = self.task_runner.tasks[name](parent=self)
        return defer.maybeDeferred(task.run, parameters)

    @classmethod
    def decode_parameters(cls, parameters):
        '''
        Process parameters string from new task goal or subtask. Should return the
        processes parameters which will be passed to the run function. By default
        returns the json decoded object in the string or, if this fails, just
        the original string.

        If this function throws an exception (such as a ParametersException), the task will be aborted.
        '''
        try:
            return json.loads(parameters)
        except ValueError:
            return parameters

    def cleanup(self):
        '''
        Will be called if a task in canceled, preempted,
        or raises an exception. Called after the run defer is canceled,
        but before any other task is run. It should therefore finish
        very quickly, and only do things like set default parameters for future
        tasks, turn off perception, etc.
        '''
        pass

    def run(self, parameters):
        '''
        The actual body of the task. Should attempt to execute whatever is expected
        of the task, using the interfaces set up in init() or the base task to
        command actuator movements, read perception output, etc. Should use self.send_feedback
        to update clients about what the task is doing at the moment. If something goes wrong,
        raise an exception describing what went wrong and the task will be aborted and cleanup is called.
        If it executes succesfully, return with defer.returnValue(message) to send a final
        result to the connected clients. Tasks can also spawn other tasks in the run function
        using run_subtask.

        @param parameters: arguments to modify the behavior of the task. By defaut will be a json decoded
                           object from the string passed in the goal, but can be changed
                           by overridding decode_parameters.
        '''
        pass
