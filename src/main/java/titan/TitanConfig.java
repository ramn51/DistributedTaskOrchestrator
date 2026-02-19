/*
 * Copyright 2026 Ram Narayanan
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
 */

package titan;

import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Properties;

public class TitanConfig {
    private static final Properties props = new Properties();

    static {
        try {
            try (InputStream input = new FileInputStream("titan.properties")) {
                props.load(input);
                System.out.println("Loaded configuration from titan.properties");
            } catch (IOException ex) {
                System.out.println("titan.properties not found. Using defaults/env vars.");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static String get(String key, String defaultValue) {
        // Ex: titan.redis.host => TITAN_REDIS_HOST
        String envKey = key.toUpperCase().replace(".", "_");
        String envVal = System.getenv(envKey);
        if (envVal != null) return envVal;

        return props.getProperty(key, defaultValue);
    }

    public static int getInt(String key, int defaultValue) {
        String val = get(key, String.valueOf(defaultValue));
        try {
            return Integer.parseInt(val);
        } catch (NumberFormatException e) {
            return defaultValue;
        }
    }
}
