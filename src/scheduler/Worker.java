package scheduler;

import java.util.Collections;
import java.util.List;

public record Worker(String host, int port, long lastSeen, List<String> capabilities){
    public Worker{
        if(capabilities == null){
            capabilities = Collections.emptyList();
        }
    }
}