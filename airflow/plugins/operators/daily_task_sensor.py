import os

from airflow.exceptions import AirflowException
from airflow.models import TaskInstance, DagBag, DagModel, DagRun
from airflow.sensors.base_sensor_operator import BaseSensorOperator
from airflow.utils.db import provide_session
from airflow.utils.decorators import apply_defaults
from airflow.utils.state import State
from datetime import datetime, timedelta


class DailyExternalTaskSensor(BaseSensorOperator):
    """
    Waits for a different DAG or a task in a different DAG to complete for a
    specific execution_date
    :param external_dag_id: The dag_id that contains the task you want to
        wait for
    :type external_dag_id: str
    :param external_task_id: The task_id that contains the task you want to
        wait for. If ``None`` the sensor waits for the DAG
    :type external_task_id: str
    :param allowed_states: list of allowed states, default is ``['success']``
    :type allowed_states: list
    :param check_existence: Set to `True` to check if the external task exists (when
        external_task_id is not None) or check if the DAG to wait for exists (when
        external_task_id is None), and immediately cease waiting if the external task
        or DAG does not exist (default value: False).
    :type check_existence: bool
    """
    template_fields = ['external_dag_id', 'external_task_id']
    ui_color = '#ffcc99'

    @apply_defaults
    def __init__(self,
                 external_dag_id,
                 external_task_id,
                 allowed_states=None,
                 check_existence=True,
                 pool='default_pool',
                 *args,
                 **kwargs):
        current_timestamp = datetime.now()
        self.pool = pool
        self.timeout = 60*60*24 - (current_timestamp.hour * 3600 + current_timestamp.minute * 60 + current_timestamp.second)
        super().__init__(timeout=self.timeout, pool=self.pool, *args, **kwargs)
        self.allowed_states = allowed_states or [State.SUCCESS]

        if external_task_id:
            if not set(self.allowed_states) <= set(State.task_states):
                raise ValueError(
                    'Valid values for `allowed_states` '
                    'when `external_task_id` is not `None`: {}'.format(
                        State.task_states)
                )

        else:
            if not set(self.allowed_states) <= set(State.dag_states):
                raise ValueError(
                    'Valid values for `allowed_states` '
                    'when `external_task_id` is `None`: {}'.format(
                        State.dag_states)
                )

        self.external_dag_id = external_dag_id
        self.external_task_id = external_task_id
        self.check_existence = check_existence
        # we only check the existence for the first time.
        self.has_checked_existence = False
        self.unallowed_states = [
            State.FAILED, State.SKIPPED, State.UPSTREAM_FAILED, State.SHUTDOWN]

    @provide_session
    def poke(self, context, session=None):

        execution_date = context['execution_date']  

        self.log.info(
            'Poking for {}.{} on {} ... '.format(
            self.external_dag_id, self.external_task_id, execution_date.date())
        )

        self._check_existence(session)

        unallowed_count = self._query_external_count(
            session, self.unallowed_states, execution_date)

        if unallowed_count > 0:
            raise AirflowException(
                'Found {} task in {} dag to be in unallowed state.'.format(
                    self.external_task_id, self.external_dag_id))

        allowed_count = self._query_external_count(
            session, self.allowed_states, execution_date)

        self.log.info('Found {} tasks in allowed state'.format(allowed_count))

        session.commit()

        return allowed_count >= 1
   
    def _check_existence(self, session):

        DM = DagModel

        # we only do the check for 1st time, no need for subsequent poke
        if self.check_existence and not self.has_checked_existence:
            dag_to_wait = session.query(DM).filter(
                DM.dag_id == self.external_dag_id
            ).first()

            if not dag_to_wait:
                raise AirflowException('The external DAG '
                                       '{} does not exist.'.format(self.external_dag_id))
            elif not os.path.exists(dag_to_wait.fileloc):
                raise AirflowException('The external DAG '
                                        '{} was deleted.'.format(self.external_dag_id))
            elif dag_to_wait.is_paused:
                raise AirflowException('The external DAG '
                                        '{} is paused.'.format(self.external_dag_id))

            if self.external_task_id:
                refreshed_dag_info = DagBag(
                    dag_to_wait.fileloc).get_dag(self.external_dag_id)
                if not refreshed_dag_info.has_task(self.external_task_id):
                    raise AirflowException('The external task '
                                           '{} in DAG {} does not exist.'.format(self.external_task_id,
                                                                                 self.external_dag_id))
            self.has_checked_existence = True

    def _query_external_count(self, session, states, execution_date):

            TI = TaskInstance
            DR = DagRun

            execution_day_start = execution_date.replace(
                minute=0, hour=0, second=0, microsecond=0)
            execution_day_end = execution_day_start + timedelta(days=1)

            if self.external_task_id:
                return session.query(TI).filter(
                    TI.dag_id == self.external_dag_id,
                    TI.task_id == self.external_task_id,
                    TI.state.in_(states),
                    TI.execution_date >= execution_day_start,
                    TI.execution_date < execution_day_end
                ).count()
            else:
                return session.query(DR).filter(
                    DR.dag_id == self.external_dag_id,
                    DR.state.in_(states),
                    DR.execution_date >= execution_day_start,
                    DR.execution_date < execution_day_end
                ).count()
