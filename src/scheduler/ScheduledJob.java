package scheduler;

import java.util.concurrent.Delayed;
import java.util.concurrent.TimeUnit;

public class ScheduledJob implements Delayed {
    private final Job job;
    public ScheduledJob(Job job){
        this.job = job;
    }

    public Job getJob() {
        return job;
    }

    @Override
    public long getDelay(TimeUnit unit) {
        long diff = job.getScheduledTime() - System.currentTimeMillis();
        return unit.convert(diff, TimeUnit.MILLISECONDS);
    }

    @Override
    public int compareTo(Delayed other) {
        return Long.compare(this.getDelay(TimeUnit.MILLISECONDS), other.getDelay(TimeUnit.MILLISECONDS));
    }
}
