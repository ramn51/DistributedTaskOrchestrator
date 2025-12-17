package scheduler.tasks;

import scheduler.TaskHandler;

public class PdfConversionHandler implements TaskHandler {
    @Override
    public String execute(String payload){
        System.out.println("📄 [PDF WORKER] Converting file: " + payload);
        // Simulating heavy work
        try { Thread.sleep(3000); } catch (InterruptedException e) {}

        return "PDF_GENERATED_AT_/tmp/" + payload + ".pdf";
    }
}
